# Reviews workflow

Use `gpc_find_actions` with `reviews` to locate the Android Publisher review actions. Read reviews for the user's selected package with the typed list/get operations, preserve Google's returned pagination token when fetching another page, and use the exact package and review IDs returned by the API.

Review replies are visible to app users. Draft the reply from the review and the user's instructions, then call the typed reply action only after the user directly asks to post it. Confirm the response returned by Google before reporting that the reply was published.
