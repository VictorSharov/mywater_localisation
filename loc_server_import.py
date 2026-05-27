#!/usr/bin/env python3
"""One-shot importer: mywater_server resources/locale/*.json -> corpus (group C).

Creates the 67 server-only "group C" locale keys as NEW corpus records on the
`web` platform, carrying their existing server translations. Group A (13 codes
already in the corpus) and the 2 keys switched to corpus twins
(passowrdPlaceholder->userPassword, newPasswordWrite->nextPassword) are NOT
touched. See reports/tasks/2026-05-27_locale_group_c_importer.md (server repo).

Group C splits into:
  - 8 placeholders that are EN-only on the server (translation == lower_case
    key name, |R| in notes): we author REAL user-facing EN copy here (brand
    voice) and NO target translations — every language stays untranslated and
    is filled later via Lokalise.
  - 59 keys with a real server `en` value + 19 target translations: en is the
    source, the 19 targets are imported unverified (server translations have
    not passed Lokalise human review -> [CR-CORPUS-UNVERIFIED]).

Server file -> corpus lang: es_ES -> es; the other 19 are 1:1. `ar` has no
server file -> it stays untranslated ("") in every new record. Untranslated
languages are stored as "" with no dirty/unverified marker, matching the
generator (translations_map: value or "") so a later regenerate is byte-stable.

stdlib-only, token-free. Idempotent: a group C key already present in the corpus
is skipped (so a re-run after the operator's --apply is a no-op, not a duplicate
create). New records have no key_id -> write_records sorts them to the tail, and
loc_corpus_import creates them in Lokalise (which stamps key_id back).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CORPUS_DIR = Path("/Users/viktor/git/mywater_localisation")
CORPUS = CORPUS_DIR / "strings.ndjson"
SERVER_LOCALE = Path("/Users/viktor/git/mywater_server/resources/locale")

sys.path.insert(0, str(CORPUS_DIR))
import loc_corpus as lc  # noqa: E402

# Group A: codes already in the corpus (name == code), got +platform web earlier.
GROUP_A = {
    "appName", "short_password", "loginPasswordEmpty", "invalidCredentials",
    "wrongPassword", "userNotFound", "passwordIncorrect", "userNotFoundRestore",
    "email_incorrect", "email_taken", "login_incorrect_characters", "login_taken",
    "short_login",
}
# Removed from the server after export; their corpus twins already exist.
REMOVED = {"passowrdPlaceholder", "newPasswordWrite"}


def server_lang(stem: str) -> str:
    """Server locale filename stem -> corpus language code."""
    return "es" if stem == "es_ES" else stem


def ctx(surface: str, type_: str, context: str, constraints: str | None = None) -> str:
    """Build a corpus `context` (Lokalise description) in the canonical field
    layout (TRANSLATION_STYLE.md § Translator context). One EN block per key."""
    lines = [f"Surface: {surface}", f"  Type: {type_}", f"  Context: {context}"]
    if constraints:
        lines.append(f"  Constraints: {constraints}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 8 placeholders — authored real EN copy (NOT the lower_case_placeholder) +
# EN context, NO target translations. Errors: polite, action-oriented, no blame
# (TRANSLATION_STYLE.md § Brand voice § Errors). The 4 VK codes surface to the
# user as one generic "VK sign-in failed" message, so their copy is identical
# by design — the codes stay separate.
# --------------------------------------------------------------------------- #
_VK_SIGNIN = "We couldn't sign you in with VK. Please try again."
PLACEHOLDER_EN = {
    "invalid_friend_invite": "This friend invite link is invalid or has expired. Ask your friend to send you a new one.",
    "invalid_favorite_drinks": "We couldn't update your favorite drinks. Please try again.",
    "friend_not_confirmed": "You can only do this with confirmed friends.",
    "invalid_emoji": "Please pick a single emoji.",
    "invalid_request": _VK_SIGNIN,
    "invalid_code_verifier": _VK_SIGNIN,
    "vk_token_exchange_failed": _VK_SIGNIN,
    "vk_user_resolution_failed": _VK_SIGNIN,
}

# --------------------------------------------------------------------------- #
# EN translator context for every group C key (authored from the RU `notes`).
# --------------------------------------------------------------------------- #
CONTEXT = {
    # --- 8 placeholders ---
    "invalid_friend_invite": ctx(
        "Friend invite link screen — shown when the user opens a friend invitation link.",
        "error message",
        "Returned as the `invalid_friend_invite` API error code from `mywater_server` when the invite token is missing, corrupted, signed with a different server secret, or points to an already-deleted account. The user can ask the sender for a fresh link.",
    ),
    "invalid_favorite_drinks": ctx(
        "Favorite drinks sync — shown when saving the user's favorite drinks fails.",
        "error message",
        "Returned as the `invalid_favorite_drinks` API error code from `mywater_server` (`updateUser.php` type=favoriteDrinks) when the client omits deviceId, sends `drinks` that is not JSON / not a list of objects, or includes invalid drinkTag, volume, or orderInList fields. A technical client-packet error shown to the user as a generic failure.",
    ),
    "friend_not_confirmed": ctx(
        "Friend endorsement action — shown when reacting to another user.",
        "error message",
        "Returned as the `friend_not_confirmed` API error code from `mywater_server` (`setFriendEndorsement.php`) when the target user exists but is not a confirmed friend of the signed-in user.",
    ),
    "invalid_emoji": ctx(
        "Friend endorsement action — validation error when choosing a reaction emoji.",
        "error message",
        "Returned as the `invalid_emoji` API error code from `mywater_server` (`setFriendEndorsement.php`) when the emoji value is not exactly one valid emoji grapheme cluster (invalid UTF-8, plain text, multiple emoji, or control characters).",
        constraints="Keep short.",
    ),
    "invalid_request": ctx(
        "VK sign-in flow — shown when signing in with VK fails.",
        "error message",
        "Returned as the `invalid_request` API error code from `mywater_server` (`exchangeVKAuthCode.php`) when a required VK ID OAuth parameter is empty, `code` exceeds 1024 characters, or `redirect_uri` does not match the server whitelist. A technical code; the user sees a generic VK sign-in error.",
    ),
    "invalid_code_verifier": ctx(
        "VK sign-in flow — shown when signing in with VK fails.",
        "error message",
        "Returned as the `invalid_code_verifier` API error code from `mywater_server` (`exchangeVKAuthCode.php`) when the PKCE `code_verifier` is shorter than 43 or longer than 128 characters, or contains characters outside RFC 7636. Indicates a client PKCE bug; the user sees a generic VK sign-in error.",
    ),
    "vk_token_exchange_failed": ctx(
        "VK sign-in flow — shown when signing in with VK fails.",
        "error message",
        "Returned as the `vk_token_exchange_failed` API error code from `mywater_server` (`exchangeVKAuthCode.php`) when exchanging the authorization code for tokens fails (invalid_grant, expired code, wrong client_secret, missing user_id/access_token, or a failed id_token check). The user sees a generic VK sign-in error; retrying usually resolves it.",
    ),
    "vk_user_resolution_failed": ctx(
        "VK sign-in flow — shown when signing in with VK fails.",
        "error message",
        "Returned as the `vk_user_resolution_failed` API error code from `mywater_server` (`exchangeVKAuthCode.php`) when the `users.get` call after a successful code exchange fails (VK API unavailable or malformed response). A rare infrastructure error; retrying may succeed.",
    ),
    # --- 8 password-reset email / form keys ---
    "resetButton": ctx(
        "Password reset email — call-to-action button linking to the reset form.",
        "button label",
        "Label of the button in the password reset email that opens the reset form. The same string is also reused as the email subject line.",
        constraints="Keep short; no trailing period.",
    ),
    "restoreRequsetText": ctx(
        "Password reset email body — main paragraph.",
        "paragraph",
        "Main body paragraph of the password reset email; explains that a reset was requested and prompts the user to tap the button below to set a new password.",
    ),
    "wrongMail": ctx(
        "Password reset email body — closing disclaimer paragraph.",
        "paragraph",
        "Disclaimer at the end of the password reset email telling a recipient who did not request a reset that the email can be safely ignored.",
    ),
    "buttonNotWorking": ctx(
        "Password reset email body — fallback-instructions paragraph.",
        "paragraph",
        "Technical fallback paragraph in the password reset email; instructs the user to copy and paste the reset URL into a browser if the button is not clickable in their mail client.",
    ),
    "saveButton": ctx(
        "Password reset web form — submit button.",
        "button label",
        "Submit button on the password reset web form; tapping it sends the new password to the server.",
        constraints="Keep short; no trailing period.",
    ),
    "wrongLink": ctx(
        "Password reset web form — invalid-link error text and JS submit-failure message.",
        "error message",
        "Shown on the password reset web form in two roles: as the main error when the page is opened with an invalid or expired link, and (stored in a button data-attribute) as the generic message JavaScript shows when a submit fails — server returned plain-text NO (invalid/expired token, exhausted attempts) or a network error.",
    ),
    "wrongLinkHelp": ctx(
        "Password reset web form — secondary text on the invalid-link error page.",
        "paragraph",
        "Second paragraph shown together with `wrongLink` on the invalid-link error page; tells the user how to obtain a new working reset link.",
    ),
    "resetSuccess": ctx(
        "Password reset web form — success message.",
        "paragraph",
        "Success message on the password reset web form; stored in a hidden data-attribute and shown by JavaScript (which removes the form) after the new password is saved.",
    ),
    # --- 51 error codes ---
    "long_password": ctx(
        "Password reset web form — length validation message.",
        "error message",
        "Shown only on the password reset web form (not in the app); stored in a hidden data-attribute and shown by JavaScript when the server returns the exact plain-text `long_password` response. Length is checked server-side before the nonce/link check. The app's `api.long_password` is a separate key.",
    ),
    "generic_error": ctx(
        "Mobile app — fallback error message.",
        "error message",
        "Fallback shown in `error_localized` when the server returns an error status but no specific code. The user sees it when the cause is unknown.",
    ),
    "long_login": ctx(
        "Registration / profile login change — length validation error.",
        "error message",
        "Returned in the API `errors[]` array when the login (username) exceeds 50 characters during registration or a profile login change.",
    ),
    "long_name": ctx(
        "Profile name editor — length validation error.",
        "error message",
        "Returned by `setUserName` / `changeProfile` when the display name exceeds 30 characters (counted by graphemes, as a human perceives them, not bytes).",
    ),
    "empty_name": ctx(
        "Profile name editor — validation error.",
        "error message",
        "Returned by `setUserName` / `changeProfile` when the user tries to save an empty display name.",
    ),
    "friend_self_request": ctx(
        "Add friend — error.",
        "error message",
        "Returned when the user tries to add their own account as a friend; the server compares the current user's ID with the target ID and rejects the request.",
    ),
    "friend_not_found": ctx(
        "Add friend — error.",
        "error message",
        "Returned when adding a friend whose user ID does not exist in the system.",
    ),
    "invalidDrinkData": ctx(
        "Drink sync — error.",
        "error message",
        "Returned when syncing drink records and the payload is missing, not valid JSON, not decoded as an array, or an empty array. Occurs when adding or deleting drink entries.",
    ),
    "invalidWeightData": ctx(
        "Weight sync — error.",
        "error message",
        "Returned when syncing body-weight records and the payload is missing, not valid JSON, not decoded as an array, or an empty array. Occurs when adding or deleting weight entries.",
    ),
    "invalidOwnDrinkData": ctx(
        "Custom drinks sync — error.",
        "error message",
        "Returned when saving user-defined drink types (custom recipes) and the payload is invalid JSON, an empty array, or a single record fails validation (bad tag id, color, caffeine value, etc.).",
    ),
    "invalidPagination": ctx(
        "List requests (friends, stats, search, profile) — error.",
        "error message",
        "Returned when the `count` or `offset` pagination parameters are non-numeric or out of range (e.g. count > 100 for friends, offset > 10000). Used across several API requests.",
    ),
    "uploadedfile_missing": ctx(
        "Avatar upload — error.",
        "error message",
        "Returned when uploading a profile avatar but no image file was attached and no avatar-delete command was given either.",
    ),
    "avatar_too_large": ctx(
        "Avatar upload — size error.",
        "error message",
        "Returned when the avatar file exceeds 5 MB, a side is larger than 2048 px, or the total exceeds 4 megapixels. May be returned by app code (PHP) or generated by the web server (nginx) on an oversized request body.",
    ),
    "avatar_upload_failed": ctx(
        "Avatar upload — technical error.",
        "error message",
        "Returned on a technical avatar-processing failure unrelated to size limits: a non-size PHP upload error, a corrupted or unsupported image, or a failure to store the avatar in cloud storage (S3).",
    ),
    "save_failed": ctx(
        "app-wide — generic save error.",
        "error message",
        "Generic data-save failure: the server could not write or apply changes to storage (usually a DB write/transaction failure, sometimes a storage call before the write). Used when updating profile settings, drinks, weights, and other user data.",
    ),
    "missing_parameters": ctx(
        "User settings update / friend endorsement — error.",
        "error message",
        "Returned when one or more required fields are missing, empty, or malformed for the request type — primarily the dailyNorm, defaultVolumes, orderOfDrinks, and hiddenDefaultDrinks branches, and when `setFriendEndorsement.php` receives a missing or invalid day.",
    ),
    "missing_credentials": ctx(
        "Sign-in — error.",
        "error message",
        "Returned at sign-in when the login or password is missing (empty fields). On Android v2 clients this code is remapped to `loginPasswordEmpty`.",
    ),
    "missing_device_id": ctx(
        "Data sync / friend endorsement — error.",
        "error message",
        "Returned when the required deviceId/device_id is absent — on update requests (`getNewUpdates.php`) and `setFriendEndorsement.php`, where deviceId drives same-device incremental sync filtering.",
    ),
    "invalid_access_token": ctx(
        "Social sign-in / social friend search — error.",
        "error message",
        "Returned when the social network access token is missing or an empty string. Applies to Apple, VK, and Facebook.",
    ),
    "incorrect_provider": ctx(
        "Social sign-in / social friend search — error.",
        "error message",
        "Returned when the named social network is not supported. Supported: Apple, VK, Facebook (friend search: VK and Facebook only).",
    ),
    "multiple_social_providers": ctx(
        "Social friend search — error.",
        "error message",
        "Returned when tokens for more than one social network (e.g. VK and Facebook) are sent in a single request; only one network may be searched per call.",
    ),
    "payment_failed": ctx(
        "Payment / subscription flow — shown when a purchase or subscription activation fails.",
        "error message",
        "Returned as the `payment_failed` API error code from `mywater_server` when an Apple/Google receipt fails verification, transaction data is unrecognized, or a DB transaction fails. Generic payment-process failure.",
    ),
    "payment_verification_unavailable": ctx(
        "Payment flow (Apple transaction-id path) — error.",
        "error message",
        "Apple-only error (StoreKit 2 / original transaction id): Apple's server is temporarily unreachable due to connectivity or authentication issues. A transient infrastructure problem, not bad payment data.",
    ),
    "missingPaymentProof": ctx(
        "Payment flow — warning when no proof of payment was received.",
        "warning message",
        "Warning (not an error): no usable proof of payment was received — no Android token, no Apple transaction id, and no uploaded receipt file (an empty trimmed androidToken and legacy reciept/reciept2 text fields without an uploaded file also map here). Returned as a warning; the app should handle it as such.",
    ),
    "password_change_failed": ctx(
        "Profile password change — error.",
        "error message",
        "Returned when changing the password in profile settings fails to replace it while preserving the current auth token — usually a write/transaction failure, but also when the required token for this operation was not supplied.",
    ),
    "social_friends_fetch_failed": ctx(
        "Social friend search — error.",
        "error message",
        "Returned when loading the friends list from VK or Facebook fails: the token may be valid but the social network API request failed.",
    ),
    "invalid_transaction_id": ctx(
        "Payment flow (Apple) — data-format error.",
        "error message",
        "Returned when the supplied Apple transaction id contains non-numeric characters or exceeds the allowed length (over 30 characters).",
    ),
    "invalid_subscription_data": ctx(
        "Subscription activation (Google Play) — error.",
        "error message",
        "Returned when `receipt_data_android` cannot be decoded as Base64 JSON, or the required `subscription_id` and `token` fields are missing or empty.",
    ),
    "subscription_expired": ctx(
        "Subscription activation / verification — error.",
        "error message",
        "Returned when verification with Apple or Google succeeds but the subscription has already expired at processing time. Used for both Apple and Google Play.",
    ),
    "subscription_verification_failed": ctx(
        "Subscription activation (Google Play) — error.",
        "error message",
        "Returned when the request reaches Google but Google reports the token does not correspond to a valid active subscription (wrong token, revoked purchase, or inactive subscription).",
    ),
    "unknown_update_type": ctx(
        "User settings update — error.",
        "error message",
        "Returned when the `type` parameter does not match any known operation; can occur with an outdated or non-standard app version.",
    ),
    "email_send_failed": ctx(
        "Password reset request — error.",
        "error message",
        "Returned when the password reset email could not be sent, or the matched account has no stored email address. Shown as a generic fallback without revealing account state through this public endpoint; the social-sign-in hint is phrased conditionally.",
    ),
    "too_many_requests": ctx(
        "app-wide rate limit — error.",
        "error message",
        "Rate-limit / anti-abuse error used in several protective branches: repeated failed sign-in or registration attempts, repeated password reset requests, and social sign-in / social account linking when protective counters trip. Signals a temporary block, not bad user data.",
    ),
    "undefindedError": ctx(
        "Android v2 compatibility — generic error.",
        "error message",
        "Compatibility code for old Android v2 clients only; never emitted directly — the server remaps many specific errors (avatar, name, password change, etc.) to this code for those legacy clients. Newer apps receive specific codes. Key spelling preserves the historical typo (undefinded).",
    ),
    "batch_too_large": ctx(
        "Batch sync — error.",
        "error message",
        "Returned when a single request carries more than 500 items. Applies to batches of drink, weight, and custom-drink records.",
        constraints="Keep the limit number (500).",
    ),
    "invalid_hidden_drink_ids": ctx(
        "Hidden default drinks update — error.",
        "error message",
        "Returned when the array of standard-drink IDs the user has hidden from their interface contains non-numeric identifiers.",
    ),
    "self_profile_not_supported": ctx(
        "View another user's profile (`getProfile.php`) — error.",
        "error message",
        "Returned by `getProfile.php` when the signed-in user's own ID is passed; this endpoint is only for viewing other people's profiles, not your own.",
    ),
    "serverBusy": ctx(
        "app-wide — system error.",
        "error message",
        "System error: the app server is overloaded or temporarily unavailable (PHP not responding; 502/503/504). Generated by the web server (nginx), not app code — PHP does not even start.",
    ),
    "internalError": ctx(
        "app-wide — system error.",
        "error message",
        "Internal server error on uncaught exceptions (HTTP 500+) or a data-invariant violation (e.g. a user profile could not be read right after creation). Used across several services.",
    ),
    "socialauth_error": ctx(
        "Social sign-in / account linking — error.",
        "error message",
        "Returned when signing in with a social network (Apple, VK, Facebook) or linking one to an account fails: the external provider returned an error or invalid/missing user data. The token may be non-empty but the social API request still failed.",
    ),
    "account_is_already_linked_to_another_user": ctx(
        "Social account linking — error.",
        "error message",
        "Returned when linking a social account that is already linked to a different app user; one social account cannot be linked to multiple profiles at once.",
    ),
    "login_is_invalid": ctx(
        "Password reset request — empty-field error.",
        "error message",
        "Returned during a password reset request when the login/email field is empty — the user did not fill the required field before submitting.",
    ),
    "invalidUserId": ctx(
        "View another user's profile — input-format error.",
        "error message",
        "Returned when the `user_id` for viewing another profile is missing, non-numeric, or <= 0. An input-format error, not a missing user.",
    ),
    "drinkNotFound": ctx(
        "Delete drink records — error.",
        "error message",
        "Returned when no item in the delete batch carries the full record key (drinkTimestamp, drinkDay, drinkRandomToken), so there is literally nothing to delete. Does not mean a valid record was found and already deleted.",
    ),
    "invalidFriendId": ctx(
        "Add / remove friend — input-format error.",
        "error message",
        "Returned when the supplied user ID is non-numeric or <= 0. An input-format error, not a missing user.",
    ),
    "empty query param": ctx(
        "User search — empty-query error.",
        "error message",
        "Returned when the search query is empty or whitespace only. The key name contains spaces — a historical API contract.",
    ),
    "too short query param": ctx(
        "User search — too-short-query error.",
        "error message",
        "Returned when the search query is shorter than 3 characters (UTF-8 characters). The key name contains spaces — a historical API contract.",
    ),
    "search unavailable": ctx(
        "User search — infrastructure error.",
        "error message",
        "Returned when the search engine (Manticore Search) is unavailable or the query itself failed with an internal error. A transient infrastructure problem. The key name contains a space — a historical API contract.",
    ),
    "receipt_too_large": ctx(
        "Payment flow (Apple) — receipt size error.",
        "error message",
        "Returned when the uploaded Apple receipt file exceeds the allowed size. May come from app code (PHP) or the web server (nginx, HTTP 413) before PHP runs.",
    ),
    "emptyReciept": ctx(
        "Payment flow (Apple) — empty receipt error.",
        "error message",
        "Returned when an Apple receipt file was uploaded but is empty or unreadable by the server. Key spelling preserves the historical typo (Reciept).",
    ),
    "short token": ctx(
        "Apple Search Ads attribution — token pre-check error.",
        "error message",
        "Returned when the Apple Search Ads attribution token fails a synchronous pre-check: too short, too long, or not valid-looking Base64. A technical code the user usually does not see directly. The key name contains a space — a historical API contract.",
    ),
}

# Canonical record field order (generator order + transient local markers before t).
_FIELD_ORDER = ["key_id", "key", "platforms", "plural", "archived", "en", "context",
                "unverified", "dirty", "dirty_meta", "t"]


def canonical(record: dict) -> dict:
    out = {field: record[field] for field in _FIELD_ORDER if field in record}
    for key, value in record.items():
        if key not in out:
            out[key] = value
    return out


def build() -> int:
    en_pack = json.loads((SERVER_LOCALE / "en.json").read_text(encoding="utf-8"))
    group_c = [k for k in en_pack if k not in GROUP_A and k not in REMOVED]
    if len(group_c) != 67:
        raise SystemExit(f"expected 67 group C keys, derived {len(group_c)}")
    if set(CONTEXT) != set(group_c):
        raise SystemExit(
            f"CONTEXT keys != group C: "
            f"missing={sorted(set(group_c) - set(CONTEXT))} "
            f"extra={sorted(set(CONTEXT) - set(group_c))}"
        )

    # corpus_lang -> {key: translation string}
    packs: dict[str, dict[str, str]] = {}
    for path in sorted(SERVER_LOCALE.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        packs[server_lang(path.stem)] = {
            key: (value["translation"] if isinstance(value, dict) else value)
            for key, value in data.items()
        }

    records = lc.read_records(CORPUS)
    index = lc.index_by_key_name(records)
    corpus_langs = lc.known_langs(records)  # all 21 project languages

    new_records: list[dict] = []
    skipped: list[str] = []
    for key in group_c:
        if key in index:
            skipped.append(key)
            continue
        record: dict = {"key": key}
        lc.set_platforms(record, ["web"])
        lc.set_context(record, CONTEXT[key])
        if key in PLACEHOLDER_EN:
            lc.set_translation(record, "en", PLACEHOLDER_EN[key])
        else:
            lc.set_translation(record, "en", packs["en"][key])
            for lang in sorted(packs):
                if lang == "en":
                    continue
                value = packs[lang].get(key)
                if value and value.strip():
                    lc.set_translation(record, lang, value)  # unverified + dirty
        # Fill every untranslated project language with "" (no marker) to match
        # the generator's all-languages `t` shape -> byte-stable on regenerate.
        for lang in corpus_langs:
            record.setdefault("t", {}).setdefault(lang, "")
        new_records.append(canonical(record))

    if skipped:
        print(f"SKIP (already in corpus, no re-create): {len(skipped)} -> {skipped}")
    lc.write_records(CORPUS, records + new_records)
    print(f"added {len(new_records)} new corpus records (group C)")
    return len(new_records)


if __name__ == "__main__":
    build()
