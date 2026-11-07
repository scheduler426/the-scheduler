# Design decisions

Decisions and open questions that come up while implementing the task briefs. Each entry says what the question is, why it matters, the options, and what was decided.

## 1. Does console mail mode need a sender address? (decided: option 1)

**Where:** `EmailService.sendEmail` (D1-2, issue #5), used by sign-up (D1-5, #8) and password reset (D1-4, #7).

**Background:** `EmailService` sends every email the app produces. It has two modes:

- **Real mode:** `mailHost` is an SMTP server. The email goes to a real inbox.
- **Console mode:** `mailHost="console"`. The email is printed instead of sent. Tests and local development use this so nobody needs a mail server.

**The conflict between tasks:**

- D1-2 says `sendEmail` raises `MailDeliveryError` when the host is empty **or the sender address is missing**, and lists that check before the console check.
- D1-2 also says `buildApplication` creates `EmailService(host=mailHost)` with no sender, so the sender comes only from the `SCHEDULER_SMTP_FROM` environment variable.
- D1-5's tests expect that, with `mailHost="console"` and no environment variables, registering returns `ok` and prints a confirmation.
- D1-4's tests expect `requestResetLink` to print the reset email in the same setup.

Followed literally, D1-2 makes registration return `mailFailed` (the account is still created) and makes the reset email silently not print, unless every test and developer sets `SCHEDULER_SMTP_FROM`.

**Options:**

1. **Require a sender only for real SMTP hosts.** Console mode prints the email even with no sender. Nothing is sent in console mode, so a "From" address has no effect there. Real mode still fails loudly when the sender is missing.
2. **Follow D1-2 literally.** Always require a sender. Tests set `SCHEDULER_SMTP_FROM` (for example with `monkeypatch.setenv`), and developers must set it locally.
3. **Default the sender in `buildApplication`.** Keep the check in `EmailService`, but pass a default such as `noreply@ilstu.edu` when none is configured. This also means real mode would send from that default if someone forgets to configure it.

**Decision:** option 1. An empty host always raises `MailDeliveryError`. A missing sender raises only when the host is a real SMTP server. Console mode prints the email with or without a sender, so tests and local development need no mail settings. This applies the same way to `sendEmail`, `sendBulkEmail`, and `sendEmailWithAttachment`.
