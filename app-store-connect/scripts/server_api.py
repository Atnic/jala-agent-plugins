"""Read-only StoreKit API operations and verified reconciliation exports."""

import csv
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import requests
from appstoreserverlibrary.api_client import AppStoreServerAPIClient, APIException, GetTransactionHistoryVersion
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.TransactionHistoryRequest import TransactionHistoryRequest, ProductType, Order
from appstoreserverlibrary.models.InAppOwnershipType import InAppOwnershipType
from appstoreserverlibrary.models.NotificationHistoryRequest import NotificationHistoryRequest
from appstoreserverlibrary.models.NotificationTypeV2 import NotificationTypeV2
from appstoreserverlibrary.models.Subtype import Subtype
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException

import server_store

HOSTS = {"production": "api.storekit.apple.com", "sandbox": "api.storekit-sandbox.apple.com"}
FIELDS = ("originalTransactionId", "transactionId", "productId", "purchaseDate", "revocationDate",
          "revocationReason", "environment", "appAccountToken", "currency", "price", "quantity")
DATE_FIELDS = ("purchaseDate", "revocationDate", "originalPurchaseDate", "signedDate")


class ReadOnlyClient(AppStoreServerAPIClient):
    """Bound the SDK transport to these four reading endpoints, including history POST."""

    def _execute_request(self, method, url, params, headers, json, data):
        parsed = urlsplit(url)
        allowed_get = re.fullmatch(r"/inApps/(?:v1/transactions/[0-9]+|v2/history/[0-9]+|v2/refund/lookup/[0-9]+)", parsed.path)
        if (parsed.scheme != "https" or parsed.netloc not in HOSTS.values() or parsed.query or parsed.fragment
                or not ((method == "GET" and allowed_get)
                        or (method == "POST" and parsed.path == "/inApps/v1/notifications/history"))):
            raise ValueError("Only the four supported read-only StoreKit operations are allowed.")
        return requests.request(method, url, params=params, headers=headers, json=json, data=data,
                                timeout=30, allow_redirects=False)


def services(connection, environment):
    if environment not in HOSTS:
        raise ValueError("Choose production or sandbox explicitly.")
    env = Environment.PRODUCTION if environment == "production" else Environment.SANDBOX
    api = ReadOnlyClient(connection["private_key"].encode(), connection["key_id"],
                         connection["issuer_id"], connection["bundle_id"], env)
    roots = [p.read_bytes() for p in sorted((Path(__file__).parents[1] / "assets" / "apple-roots").glob("*.cer"))]
    if not roots:
        raise ValueError("Bundled Apple root certificates are missing. Repair the plugin installation.")
    verifier = SignedDataVerifier(roots, True, env, connection["bundle_id"], connection["app_apple_id"])
    return api, verifier


def scalar(value):
    return value.value if isinstance(value, Enum) else value


def transaction(verifier, signed):
    if not isinstance(signed, str) or not signed:
        raise ValueError("Apple omitted a required signed transaction. No verified export was produced.")
    payload = verifier.verify_and_decode_signed_transaction(signed)
    result = {field: scalar(getattr(payload, field, None)) for field in FIELDS}
    if any(not isinstance(result[field], str) or not result[field]
           for field in ("originalTransactionId", "transactionId", "productId")):
        raise ValueError("Verified payload omitted a required transaction identifier.")
    if type(result["purchaseDate"]) is not int or result["purchaseDate"] < 0:
        raise ValueError("Verified payload omitted a valid purchaseDate.")
    for field in DATE_FIELDS:
        stamp = getattr(payload, field, None)
        if stamp is not None and (type(stamp) is not int or stamp < 0):
            raise ValueError("Verified payload contained an invalid timestamp.")
        result[field] = stamp
        result[field + "UTC"] = (datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()
                                  if stamp is not None else None)
    return result


def filters(raw, notifications=False):
    fields = ({"startDate", "endDate", "notificationType", "notificationSubtype", "onlyFailures", "transactionId"}
              if notifications else {"startDate", "endDate", "productIds", "productTypes", "sort",
                                     "subscriptionGroupIdentifiers", "inAppOwnershipType", "revoked"})
    if set(raw) - fields:
        raise ValueError("Unknown history filter: " + ", ".join(sorted(set(raw) - fields)))
    value = dict(raw)
    for key in ("startDate", "endDate"):
        if key in value and (type(value[key]) is not int or value[key] < 0):
            raise ValueError(key + " must be UNIX milliseconds, as a nonnegative integer.")
    if notifications and not {"startDate", "endDate"} <= set(value):
        raise ValueError("Notification history requires startDate and endDate UNIX milliseconds.")
    if "startDate" in value and "endDate" in value and value["startDate"] >= value["endDate"]:
        raise ValueError("startDate must precede endDate.")
    for key in ("revoked", "onlyFailures"):
        if key in value and type(value[key]) is not bool:
            raise ValueError(key + " must be a boolean.")
    for key in ("productIds", "productTypes", "subscriptionGroupIdentifiers"):
        if key in value and (not isinstance(value[key], list) or not value[key]
                             or not all(isinstance(v, str) and v for v in value[key])):
            raise ValueError(key + " must be a nonempty array of strings.")
    enums = {"notificationType": NotificationTypeV2, "notificationSubtype": Subtype,
             "sort": Order, "inAppOwnershipType": InAppOwnershipType}
    for key, enum in enums.items():
        if key in value:
            value[key] = enum(value[key])
            if value[key] is None:
                raise ValueError("Unsupported value for " + key)
    if "productTypes" in value:
        value["productTypes"] = [ProductType(v) for v in value["productTypes"]]
        if any(v is None for v in value["productTypes"]):
            raise ValueError("Unsupported productTypes value.")
    if "transactionId" in value:
        identifier(value["transactionId"])
    return NotificationHistoryRequest(**value) if notifications else TransactionHistoryRequest(**value)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,64}", value):
        raise ValueError("Transaction ID must contain only digits; use a genuine store transaction ID.")
    return value


def collect(args, api, verifier, read_arguments, bundle_id, app_apple_id):
    operation = args.server_command
    cursor = getattr(args, "cursor", None)
    raw = read_arguments(args.body) if operation == "notification-history" else (
        read_arguments(args.query) if operation == "transaction-history" else {})
    request_filter = filters(raw, operation == "notification-history") if operation in {
        "transaction-history", "notification-history"} else None
    max_pages = getattr(args, "max_pages", 1)
    if not 1 <= max_pages <= 1000:
        raise ValueError("max-pages must be between 1 and 1000.")
    start, end = getattr(args, "revocation_start", None), getattr(args, "revocation_end", None)
    if any(v is not None and v < 0 for v in (start, end)) or (start is not None and end is not None and start >= end):
        raise ValueError("Use a valid inclusive revocation-start / exclusive revocation-end millisecond range.")
    rows, notices, seen = [], [], set()
    scope = "attempted-notification-deliveries" if operation == "notification-history" else "customer"
    if operation != "notification-history":
        tid = identifier(args.transaction_id)
    for page_number in range(1, max_pages + 1):
        if operation in {"verify", "transaction-info"}:
            page = api.get_transaction_info(tid)
            rows.append(transaction(verifier, page.signedTransactionInfo))
            more, next_cursor = False, None
            scope = "single-transaction"
        elif operation == "transaction-history":
            page = api.get_transaction_history(tid, cursor, request_filter, GetTransactionHistoryVersion.V2)
            if scalar(page.environment) != ("Production" if args.environment == "production" else "Sandbox"):
                raise ValueError("History response environment does not match the requested environment.")
            if page.bundleId != bundle_id:
                raise ValueError("History response bundle ID does not match this profile.")
            if not isinstance(page.signedTransactions, list):
                raise ValueError("Apple omitted the transaction list; completeness cannot be established.")
            rows.extend(transaction(verifier, item) for item in page.signedTransactions)
            more, next_cursor = page.hasMore, page.revision
        elif operation == "refund-history":
            page = api.get_refund_history(tid, cursor)
            if not isinstance(page.signedTransactions, list):
                raise ValueError("Apple omitted the refund list; completeness cannot be established.")
            rows.extend(transaction(verifier, item) for item in page.signedTransactions)
            more, next_cursor = page.hasMore, page.revision
        elif operation == "notification-history":
            page = api.get_notification_history(cursor, request_filter)
            if not isinstance(page.notificationHistory, list):
                raise ValueError("Apple omitted notification history; completeness cannot be established.")
            for item in page.notificationHistory:
                notice = verifier.verify_and_decode_notification(item.signedPayload)
                info = {"notificationUUID": notice.notificationUUID,
                        "notificationType": scalar(notice.notificationType),
                        "subtype": scalar(notice.subtype), "notificationSignedDate": notice.signedDate,
                        "notificationSignedDateUTC": (datetime.fromtimestamp(notice.signedDate / 1000, timezone.utc).isoformat()
                                                       if notice.signedDate is not None else None)}
                notices.append(info)
                signed = getattr(notice.data, "signedTransactionInfo", None) if notice.data else None
                if signed:
                    rows.append({**transaction(verifier, signed), **info})
            more, next_cursor = page.hasMore, page.paginationToken
        else:
            raise ValueError("Unsupported Server API operation.")
        if type(more) is not bool:
            raise ValueError("Apple omitted hasMore; completeness cannot be established.")
        if not more:
            break
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen or next_cursor == cursor:
            raise ValueError("Apple returned a missing or repeated pagination cursor; completeness cannot be established.")
        seen.add(next_cursor)
        cursor = next_cursor
    duplicates_removed = 0
    if operation in {"transaction-history", "refund-history"}:
        # Apple can repeat an updated transaction across pages. These commands
        # expose one current snapshot per ID, unlike notification event history.
        unique = {}
        for row in rows:
            previous = unique.get(row["transactionId"])
            if previous is not None:
                duplicates_removed += 1
            if (previous is None or row["signedDate"] is None or previous["signedDate"] is None
                    or row["signedDate"] >= previous["signedDate"]):
                unique[row["transactionId"]] = row
        rows = list(unique.values())
    if start is not None or end is not None:
        rows = [r for r in rows if r["revocationDate"] is not None
                and (start is None or r["revocationDate"] >= start)
                and (end is None or r["revocationDate"] < end)]
    return {"operation": operation, "profile": args.profile, "environment": args.environment,
            "bundleId": bundle_id, "appAppleId": app_apple_id,
            "requestedTransactionId": raw.get("transactionId") if operation == "notification-history" else tid,
            "verified": True, "complete": not more, "scope": scope,
            "startedFromCursor": getattr(args, "cursor", None) is not None,
            "pages": page_number, "nextCursor": next_cursor if more else None,
            "duplicateSnapshotsRemoved": duplicates_removed,
            "filters": raw, "revocationFilter": {"startInclusive": start, "endExclusive": end},
            "transactions": rows, "notifications": notices,
            "note": "Completeness applies only to this request scope. Customer history does not enumerate every app customer; notification history covers attempted deliveries, not all purchases. Notification transactions reflect their state at delivery."}


def export(result, destination, format):
    path = Path(destination).expanduser()
    if not path.is_absolute():
        raise ValueError("Export destination must be an absolute new file path.")
    created = []
    try:
        with path.open("x", encoding="utf-8", newline="") as output:
            created.append(path)
            if format == "json":
                json.dump(result, output, indent=2)
            else:
                columns = list(FIELDS) + [f + "UTC" for f in DATE_FIELDS] + ["originalPurchaseDate", "signedDate", "notificationUUID", "notificationType", "subtype", "notificationSignedDate", "notificationSignedDateUTC"]
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerows(result["transactions"])
        if format == "csv":
            sidecar = Path(str(path) + ".metadata.json")
            with sidecar.open("x", encoding="utf-8") as output:
                created.append(sidecar)
                json.dump({k: v for k, v in result.items() if k != "transactions"}, output, indent=2)
    except OSError:
        for file in created:
            file.unlink(missing_ok=True)
        raise ValueError("Export failed. Use a new writable destination; existing files are never overwritten.") from None
    return {"file": str(path), "format": format, "complete": result["complete"], "verified": True,
            "rows": len(result["transactions"]), **({"metadataFile": str(sidecar)} if format == "csv" else {})}


def execute(args, read_arguments):
    server_store.profile_name(args.profile)
    command = args.server_command
    if command in {"setup", "status", "forget"}:
        return getattr(server_store, command)(args.profile)
    try:
        connection = server_store.load(args.profile)
        api, verifier = services(connection, args.environment)
        result = collect(args, api, verifier, read_arguments, connection["bundle_id"], connection["app_apple_id"])
        if command == "verify":
            server_store.mark_verified(args.profile, args.environment, connection)
            return {"profile": args.profile, "environment": args.environment, "authenticationVerified": True,
                    "transactionVerified": True, "bundleId": connection["bundle_id"],
                    "note": "Transaction signature, bundle and environment checked. Apple app ID is checked on notification payloads; it is not present in transaction payloads."}
        if args.output_file:
            return export(result, args.output_file, args.format)
        if args.format == "csv":
            raise ValueError("CSV export requires --output-file so completeness metadata can accompany it.")
        return result
    except APIException as error:
        code = error.http_status_code
        kind = {401: "unauthenticated", 403: "forbidden", 404: "not-found", 429: "rate-limited"}.get(code, "apple-api-error")
        return {"error": {"status": code, "kind": kind, "appleErrorCode": error.raw_api_error,
                          "message": "Apple did not complete this read. Check the Server API key/issuer pairing, app and environment for authentication failures; no automatic retry was made."},
                "complete": False, "transactions": None}
    except VerificationException:
        return {"error": {"kind": "signature-verification-failed",
                          "message": "Apple signed data could not be verified for the configured app/environment. No decoded data was exported."},
                "complete": False, "transactions": None}
    except requests.RequestException:
        return {"error": {"kind": "network-error", "message": "Server API read failed or timed out; no automatic retry was made."},
                "complete": False, "transactions": None}
