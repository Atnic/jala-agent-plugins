# Publishing and staged edits

Android Publisher changes to app listings, images, bundles, tracks, and related resources are commonly made through an edit. Use the relevant typed action to create an edit, read the current app state, apply the requested change, review the resulting edit contents, and call the matching `edits.commit` action only after explicit confirmation. This plugin marks every edit commit for host approval because commit applies the staged changes.

For a production release, verify the package name, track, version codes, release status, rollout fraction, and update priority in the staged request before committing. A successful commit confirms that Google accepted the API edit; it does not imply that Google Play review completed or that a staged rollout reached all users.

Actions outside edit commits that can delete resources, refund or cancel purchases, alter access, change signing, pricing, availability, or product state are marked as high impact. Review the profile and request body before approving them.
