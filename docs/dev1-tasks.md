# Dev 1 tasks: implementation brief

This file is for a coding agent (or developer) implementing all of Dev 1's tasks in this repository. It contains the project rules and every Dev 1 task, copied from the GitHub issues on [scheduler426/the-scheduler](https://github.com/scheduler426/the-scheduler/issues). Do the tasks in the order listed. Each task's **Steps** are the specification; follow them exactly (names, signatures, return values, error messages).

## The app

Illinois State students agree on one recurring meeting time for a group project. A student signs up with an `@ilstu.edu` email, creates a group, invites classmates, shares free time, votes on suggested times, and any member confirms the final time. There is no admin and no owner.

The class diagram is `docs/class-diagram.txt` (Mermaid). The code follows it, with the changes listed under "Where the code differs from the diagram" below.

## Architecture

There is **no web API**: no FastAPI, no routes, no HTTP status codes, no web server. Every feature starts at a controller and goes down:

1. **Controller** (`scheduler/controllers/`): checks the session, reads values from a `request` dict, calls one service method, and turns the result or error into a `Response`. No business rules, no SQL.
2. **Service** (`scheduler/services/`): applies the rules (membership, validation) and raises an error when one is broken.
3. **Domain class** (`scheduler/domain/`): holds rules that belong to one object, such as `Invitation.isExpired()`.
4. **Repository** (`scheduler/repositories/`): one concrete class per domain object, no interfaces. Its constructor takes a `Database` (`scheduler/infrastructure/database.py`), never `DuckDBConnection`.
5. **`DuckDBConnection`** (`scheduler/infrastructure/duckdb_connection.py`): the only `Database` implementation. All tables are created in its `_SCHEMA`.

`scheduler/application.py` (created in K2) is the composition root: `buildApplication(database, secretKey, mailHost)` builds every repository, service, and controller once and returns an `Application` holding the controllers. No other class creates its own dependencies.

### `request` and `Response`

- A `request` is a plain `dict` with camelCase keys. Protected handlers read the session token from `request["token"]`.
- `Response` (`scheduler/controllers/response.py`, built in K2) has `status`, `data`, `message`. Handlers are written as `return respond(lambda: ...)`, and `respond` maps errors to statuses:

| Error raised below the controller | `Response.status` |
| --- | --- |
| none | `ok` |
| `ValueError` | `invalid` |
| `LookupError` | `notFound` |
| `PermissionError` | `forbidden` |
| `AuthenticationError` | `unauthenticated` |
| `MailDeliveryError` | `mailFailed` |

- `message` is the error text. `data` is plain dicts (or lists of dicts) with camelCase keys.
- A public user dict is `{userId, email, firstName, lastName, allowEmailReminders}`. No `Response` ever contains `passwordHash`.

### Sessions

- `AuthController.handleLogin` returns a `token`; the caller sends it back as `request["token"]`.
- Every protected handler first calls `AuthenticationService.requireSession(request.get("token"))`, which returns the `UserSession` or raises `AuthenticationError`.
- Sessions live in memory in `SessionManager`. There is no session table.
- Handlers that do **not** check a session: `UserController.handleRegisterUser`, `AuthController.handleLogin`, `PasswordRecoveryController.handleForgotPassword`, `PasswordRecoveryController.handleResetPassword`, `MembershipController.handleDeclineInvite` (Dev 2).

## Principles to keep

- **Dependency inversion:** repositories depend on `Database`, services depend on repositories passed in, controllers depend on services passed in. Everything is wired in `buildApplication`.
- **Information expert / high cohesion:** rules live in the domain class or service that owns the data. Membership belongs to `GroupRepository` (`findMembers`, `addMember`, `removeMember`, `isMember`).
- **Controller (GRASP):** controllers are thin. One service call per handler, no rules, no SQL.
- **Low coupling:** no repository interfaces, no extra layers. Do not add classes the task does not ask for.
- **Single responsibility:** email text comes from template factories; sending goes through `EmailService` only.

## Rules for every task

- Match the existing code style: camelCase method and attribute names, `from __future__ import annotations`, a short module docstring at the top of each file describing what it does, private fields with read-only `@property` accessors on domain classes (see `scheduler/domain/group.py`).
- Passwords are stored as a PBKDF2 hash from `PasswordHasher`. A valid password is at least 8 characters with a letter and a digit.
- New tables go in `DuckDBConnection._SCHEMA`. SQL uses `?` placeholders, `ON CONFLICT`, and `RETURNING`. Never `INSERT OR IGNORE` or `INSERT OR REPLACE`.
- Do not add: FastAPI, routes, HTTP codes, a web server, a repository interface, a session table, a reset-token table, a class named `NotificationService`, an admin/owner flag.
- If your change makes an existing opening comment false, fix that sentence only. Do not do a comment pass.
- `scheduler/application.py` is shared with Dev 2 and Dev 3. Add only the lines your task needs.

## Where the code differs from the diagram

Already done in the code (do not undo):

- `GroupRosterRepository`, `UserProfileRepository`, and `SchedulingConflictReportRepository` are removed. Membership is part of `GroupRepository`.
- `MeetingPollRepository` is one concrete class, not an interface plus implementation.
- All repositories take `Database`.
- `UserSession` is a dataclass returned by `SessionManager` and `AuthenticationService.login`.

Added by Dev 1's tasks:

- Every protected controller depends on `AuthenticationService` and calls `requireSession(token)`.
- `UserService` takes `EmailService` and `AuthEmailTemplateFactory` (to send the signup confirmation).
- `PasswordRecoveryService` takes `AuthEmailTemplateFactory` and `PasswordHasher`.
- `EmailService.sendEmailWithAttachment` (used later by Dev 3).
- `SessionManager.removeSessionsForUser`.

## How to work

1. Read the existing code under `scheduler/` before starting. The tasks describe what is already there and what to change.
2. Do the tasks in this order: K1, D1-1, K2, D1-2, D1-3, D1-4, D1-5, D1-6, D1-7, N1.
3. For each task, do every step, then turn its **Test it** list into pytest tests in `tests/test_<task code>.py` (for example `tests/test_k2.py`). Use `DuckDBConnection(":memory:")` and `mailHost="console"`. Run `python -m pytest` and make sure everything passes before moving on.
4. Commit once per task with a message that names the task, for example `K2: add Response, requireSession, and buildApplication`. Do not push unless asked.
5. If a step conflicts with the code or with another step, stop and ask instead of guessing.

## Test helper

Once K2, D1-5, and D1-6 are done, any handler can be checked like this:

```python
from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection

app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
app.userController.handleRegisterUser({"email": "ada@ilstu.edu", "password": "secret12", "firstName": "Ada", "lastName": "Lovelace"})
token = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"}).data["token"]
```

# Tasks

## K1: Add the group files table and a member check (issue #2)

**Goal:** Add the database table for group files, and one method that answers "is this user in this group?".

**Start after:** nothing. You can start now.

### Steps

- [ ] **1. Add the `groupFiles` table.** In `scheduler/infrastructure/duckdb_connection.py`, inside `_SCHEMA`, add (same style as the other entries: `CREATE ... IF NOT EXISTS`, no foreign keys):
  - Sequence `fileIdSeq START 1`.
  - Table `groupFiles` with columns:
    - `fileId INTEGER PRIMARY KEY DEFAULT nextval('fileIdSeq')`
    - `groupId INTEGER NOT NULL`
    - `fileName VARCHAR NOT NULL`
    - `filePath VARCHAR NOT NULL`
    - `uploadedAt TIMESTAMP NOT NULL`
  - Do not change any existing table.

- [ ] **2. Fix the `DuckDBConnection` opening comment.** It says there is no table for group files. Change that sentence.

- [ ] **3. Add `GroupRepository.isMember(groupId, userId) -> bool`** in `scheduler/repositories/group_repository.py`.
  - One `SELECT` on `groupRoster` where `groupId = ?` and `userId = ?`.
  - Returns `True` if a row exists, `False` otherwise. Do not load users.

- [ ] **4. Delete file rows when a group is deleted.** In `GroupRepository.delete`, before the `groups` row is deleted, add `DELETE FROM groupFiles WHERE groupId = ?`. (This removes rows only. Files on disk are D2-6, #16.)

- [ ] **5. Use `isMember` in two services.**
  - `scheduler/services/group_membership_service.py`: make `_isMember(groupId, userId)` return `self._groupRepo.isMember(groupId, userId)`.
  - `scheduler/services/voting_service.py`: in `castVote`, replace the `any(member.userId == userId ...)` check with `self._groupRepo.isMember(poll.groupId, userId)`.

### Test it

1. `DuckDBConnection(":memory:")` opens without error, and `SELECT * FROM groupFiles` returns no rows.
2. Create a group with `GroupService.createGroup(userId, "G")`. `isMember(groupId, userId)` is `True`; `isMember(groupId, 999)` is `False`.
3. `GroupRepository.delete(groupId)` on a group with no files runs without a SQL error.

### Do not

- Write `GroupFileRepository` (that is D2-4, #14).
- Touch files on disk.
- Add a session, reset-token, conflict-report, or calendar-file table.

## D1-1: User sessions (done, review and close) (issue #3)

**Goal:** Confirm that logging in returns a `UserSession` object, then close this task. The code is already written.

**Start after:** nothing.

### Steps

- [ ] **1. Check `scheduler/domain/user_session.py`.** It defines `UserSession` as a `@dataclass` with these fields: `userSessionId: str`, `userId: int`, `token: str`, `loginTime: datetime`, `expiryTime: datetime`.

- [ ] **2. Check `scheduler/infrastructure/session_manager.py`.**
  - `createSession(userId)` returns a `UserSession`.
  - `getSession(token)` returns a copy of the `UserSession`, or `None` when the token is unknown, expired, or no longer valid.
  - `extendSession` and `removeSession` work as before.

- [ ] **3. Check `scheduler/services/authentication_service.py`.** `login(email, password)` returns the `UserSession`.

- [ ] **4. Run the checks below.** If they pass and the code is on `main`, close this issue.

### Test it

```python
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.infrastructure.token_provider import TokenProvider

manager = SessionManager(TokenProvider("secret"))
session = manager.createSession(5)
assert session.userId == 5 and session.token
assert manager.getSession(session.token).userId == 5
assert manager.getSession("missing") is None
copy = manager.getSession(session.token)
copy.userId = 99
assert manager.getSession(session.token).userId == 5
```

### Do not

- Change `TokenProvider`.
- Store sessions in the database.

## K2: App setup: wiring, responses, and the login check (issue #4)

**Goal:** Build the shared pieces every controller uses: the `Response` type, one function that turns errors into a status, the login check, and the function that builds the whole app.

**Start after:** K1 (#2) and D1-1 (#3).

### Steps

- [ ] **1. Create `scheduler/controllers/response.py` with class `Response`.**
  - Constructor: `Response(status: str, data=None, message: str = "")`. Store all three as attributes.
  - Add these class constants:

    | Constant | Value |
    | --- | --- |
    | `Response.OK` | `"ok"` |
    | `Response.INVALID` | `"invalid"` |
    | `Response.NOT_FOUND` | `"notFound"` |
    | `Response.FORBIDDEN` | `"forbidden"` |
    | `Response.UNAUTHENTICATED` | `"unauthenticated"` |
    | `Response.MAIL_FAILED` | `"mailFailed"` |

- [ ] **2. In the same file, add the function `respond(action) -> Response`.**
  - Call `action()`. If it returns normally, return `Response(Response.OK, data=<the result>)`.
  - Catch errors in this order and return `Response(<status>, message=str(error))`:
    1. `AuthenticationError` → `unauthenticated`
    2. `PermissionError` → `forbidden`
    3. `LookupError` → `notFound`
    4. `ValueError` → `invalid`
  - Let any other error go through uncaught.
  - Every controller handler will be written as `return respond(lambda: ...)`.

- [ ] **3. Add `AuthenticationError` to `scheduler/services/authentication_service.py`.** `class AuthenticationError(Exception)`. It must not inherit from `PermissionError`.

- [ ] **4. Add `AuthenticationService.requireSession(token) -> UserSession`** in the same file.
  - `token` is `None` or `""`: raise `AuthenticationError("Authentication required")`.
  - `self._sessionManager.getSession(token)` returns `None`: raise `AuthenticationError("Session is not active")`.
  - Otherwise return the `UserSession`.
  - Do not check group membership here.

- [ ] **5. Add `close()` to the database classes.**
  - `scheduler/infrastructure/database.py`: add abstract method `close(self) -> None` to `Database`.
  - `scheduler/infrastructure/duckdb_connection.py`: implement `close()` so it closes the DuckDB connection (skip if it already exists).

- [ ] **6. Create `scheduler/application.py` with class `Application`.**
  - Attributes: `database`, `sessionManager`, `mailHost`, and one attribute per controller, all `None` for now: `userController`, `authController`, `passwordRecoveryController`, `groupController`, `membershipController`, `groupFileController`, `availabilityController`, `schedulingController`, `voteController`, `meetingController`, `notificationController`.
  - Method `close() -> None`: calls `self.database.close()`.

- [ ] **7. In the same file, add `buildApplication(database: Database, secretKey: str, mailHost: str | None = None) -> Application`.**
  - Empty `secretKey`: raise `ValueError("secretKey is required")`.
  - Create one of each, in this order:
    - `PasswordHasher()`
    - `TokenProvider(secretKey, tokenValidityInMs=28_800_000)` (8 hours)
    - `SessionManager(tokenProvider)`
    - Repositories, each with `database`: `UserRepository`, `GroupRepository`, `GroupInvitationRepository`, `AvailabilityScheduleRepository`, `MeetingPollRepository`, `VoteRepository`, `ScheduledMeetingRepository`.
    - Services, with their current constructors: `UserService(userRepo, hasher)`, `AuthenticationService(userRepo, sessionManager, hasher)`, `GroupService(groupRepo)`, `GroupMembershipService(groupRepo, inviteRepo)`, `AvailabilityService(scheduleRepo)`, `MeetingSuggestionService(MeetingGenerator(), pollRepo, scheduleRepo)`, `VotingService(voteRepo, pollRepo, groupRepo)`, `MeetingFinalizationService(meetingRepo, pollRepo)`.
  - Store `database`, `sessionManager`, and `mailHost` on the `Application` and return it.
  - Do not build the application when the module is imported.

- [ ] **8. Create `requirements.txt`** at the repository root with two lines: `duckdb` and `pytest`.

### Test it

```python
from scheduler.application import buildApplication
from scheduler.controllers.response import respond
from scheduler.infrastructure.duckdb_connection import DuckDBConnection

app = buildApplication(DuckDBConnection(":memory:"), "test-secret")   # works
buildApplication(DuckDBConnection(":memory:"), "")                    # raises ValueError

def fails():
    raise LookupError("x")
result = respond(fails)
assert result.status == "notFound" and result.message == "x"
```

Also check: `requireSession(None)` raises `Authentication required`, `requireSession("bogus")` raises `Session is not active`, and a token from `login` returns the session.

### Do not

- Write any feature controller. Each later task adds its own.
- Change the default validity in `TokenProvider` itself.
- Add FastAPI, HTTP, or a web server.

## D1-2: Email sender (issue #5)

**Goal:** Build the one class that sends email. In test mode it prints the email instead of sending it.

**Start after:** K2 (#4).

### Steps

- [ ] **1. Create `scheduler/infrastructure/email_service.py` with `class MailDeliveryError(Exception)`.**

- [ ] **2. In the same file, create class `EmailService`.**
  - Constructor: `EmailService(host=None, port=None, sender=None, username=None, password=None)`.
  - Any argument left as `None` is read from an environment variable:

    | Argument | Environment variable | Default if both missing |
    | --- | --- | --- |
    | `host` | `SCHEDULER_SMTP_HOST` | none |
    | `port` | `SCHEDULER_SMTP_PORT` | `587` |
    | `sender` | `SCHEDULER_SMTP_FROM` | none |
    | `username` | `SCHEDULER_SMTP_USERNAME` | none |
    | `password` | `SCHEDULER_SMTP_PASSWORD` | none |

  - The constructor never raises, even with nothing set.

- [ ] **3. Add `sendEmail(to, subject, body) -> None`.**
  - Host empty or sender missing: raise `MailDeliveryError` with a message saying what is missing.
  - Host is `"console"`: print the recipient, subject, and body, and return.
  - Any other host: send with `smtplib`. If `username` is set, call `starttls()` and `login(username, password)`; otherwise send plain. Any SMTP error becomes `MailDeliveryError`.

- [ ] **4. Add `sendBulkEmail(toList, subject, body) -> None`.**
  - Call `sendEmail` once per address with the same subject and body.
  - If one fails, raise `MailDeliveryError` whose message names that address. Emails already sent stay sent.

- [ ] **5. Add `sendEmailWithAttachment(to, subject, body, filename, content: bytes) -> None`.**
  - Same rules as `sendEmail`, with `content` attached as `filename`.
  - In console mode, print the filename and the number of bytes, not the bytes.

- [ ] **6. Map the error in `respond`.** In `scheduler/controllers/response.py`, catch `MailDeliveryError` and return `Response(Response.MAIL_FAILED, message=str(error))`.

- [ ] **7. Create the sender in `scheduler/application.py`.** In `buildApplication`, create `emailService = EmailService(host=mailHost)` once and keep it in a variable so later tasks can pass it to services. Store it as `app.emailService`.

### Test it

1. `EmailService(host="console", sender="noreply@ilstu.edu").sendEmail("a@ilstu.edu", "Hi", "Body")` prints and returns.
2. `EmailService(host="", sender="x").sendEmail(...)` raises `MailDeliveryError`.
3. `buildApplication(DuckDBConnection(":memory:"), "test-secret")` with no mail settings still works.
4. `respond(<function that raises MailDeliveryError("x")>)` returns status `mailFailed`.

### Do not

- Write any email text here.
- Create a sender interface or a separate console class.
- Start a background thread.

## D1-3: Account email text (issue #6)

**Goal:** Write the text of three account emails. Nothing is sent in this task.

**Start after:** nothing. You can start now.

### Steps

- [ ] **1. Create `scheduler/infrastructure/auth_email_template_factory.py` with class `AuthEmailTemplateFactory`.**
  - Constructor sets `self.templateCache: dict[str, str] = {}`.

- [ ] **2. Add `buildConfirmationEmail(firstName: str, email: str) -> str`.**
  - Returns plain text that contains both `firstName` and `email`. Example:

    ```text
    Welcome to the scheduler, Ada.
    Your account ada@ilstu.edu is ready.
    ```

- [ ] **3. Add `buildResetEmail(token: str) -> str`.**
  - Returns plain text that contains `token` and says it resets the scheduler password. Example:

    ```text
    Use this token to reset your scheduler password: <token>
    ```

- [ ] **4. Add `buildEmailAuthenticationEmail(token: str) -> str`.**
  - Returns plain text that contains `token` and says it is a sign-in code.
  - Nothing calls this method yet. Write it anyway.

### Test it

```python
factory = AuthEmailTemplateFactory()
assert "Ada" in factory.buildConfirmationEmail("Ada", "ada@ilstu.edu")
assert "ada@ilstu.edu" in factory.buildConfirmationEmail("Ada", "ada@ilstu.edu")
assert "abc" in factory.buildResetEmail("abc")
assert "abc" in factory.buildEmailAuthenticationEmail("abc")
```

### Do not

- Send mail, open the database, or create tokens in this class.
- Put an email subject in the returned text. The caller chooses the subject.

## D1-4: Password reset service (issue #7)

**Goal:** Email a one-time reset code to a student who forgot their password, and let them use that code to set a new password.

**Start after:** D1-2 (#5) and D1-3 (#6).

### Steps

- [ ] **1. Create `scheduler/services/password_recovery_service.py` with class `PasswordRecoveryService`.**
  - Constructor: `PasswordRecoveryService(userRepo: UserRepository, tokenProvider: TokenProvider, emailService: EmailService, templateFactory: AuthEmailTemplateFactory, hasher: PasswordHasher)`.

- [ ] **2. Add `requestResetLink(email) -> None`.**
  1. Clean the address: strip spaces, lowercase. It needs text before `@` and a `.` after `@`.
  2. If the address is malformed, or `userRepo.findByEmail(email)` returns `None`: return without sending and without raising.
  3. Otherwise create the token: `tokenProvider.generateToken(f"reset:{user.userId}")`.
  4. Send one email: `emailService.sendEmail(user.email, "Reset your scheduler password", templateFactory.buildResetEmail(token))`.
  5. If the send raises, catch it and return.
  - The method behaves the same way in every case above, so a caller cannot tell which emails have accounts.

- [ ] **3. Add `completePasswordReset(token, newPassword) -> None`.**
  1. Read the payload with `tokenProvider.getPayload(token)`. If that fails, or the payload does not start with `reset:`, raise `ValueError("Invalid or expired token")`.
  2. Take the number after `reset:` and load the user with `userRepo.findById`. Missing: raise `LookupError("User not found")`.
  3. Check the new password: at least 8 characters, at least one letter, at least one digit. Otherwise raise `ValueError("Password must be at least 8 characters and include a letter and a digit")`.
  4. Save the user with `userRepo.save(User(user.userId, user.email, hasher.hash(newPassword), user.firstName, user.lastName, user.allowEmailReminders))`.
  5. Do not create a session.

- [ ] **4. Create the service in `scheduler/application.py`.**
  - In `buildApplication`, create a **second** `TokenProvider(secretKey, tokenValidityInMs=3_600_000)` (1 hour) for resets.
  - Create `PasswordRecoveryService(userRepo, resetTokenProvider, emailService, AuthEmailTemplateFactory(), hasher)` and keep it for D1-7.
  - Reset tokens are not stored anywhere: not in `SessionManager`, not in a table.

### Test it

1. Build the app with `mailHost="console"` and register a user.
2. `requestResetLink("ada@ilstu.edu")` prints one email. Copy the token from it; `getPayload(token)` is `reset:<userId>`.
3. `completePasswordReset(token, "newpass1")`. Now `hasher.verify("newpass1", user.passwordHash)` is `True`.
4. `requestResetLink("nobody@ilstu.edu")` prints nothing and does not raise.
5. `completePasswordReset(<a login token>, "newpass1")` raises `Invalid or expired token`.

### Do not

- Write `PasswordRecoveryController` (that is D1-7, #10).
- Store reset tokens.

## D1-5: Create, edit, and delete an account (issue #8)

**Goal:** Let a student sign up with an `@ilstu.edu` email, change their name or email, and delete their account.

**Start after:** K2 (#4), D1-2 (#5), D1-3 (#6).

### Steps

- [ ] **1. Require `@ilstu.edu` emails.** In `scheduler/services/user_service.py`, change `_normalizeEmail` so that after the existing checks, a domain other than `ilstu.edu` raises `ValueError("Email must end with @ilstu.edu")`.

- [ ] **2. Add `UserService._validatePassword(password) -> None`.**
  - Fewer than 8 characters, no letter, or no digit: raise `ValueError("Password must be at least 8 characters and include a letter and a digit")`.
  - Call it in `registerUser` before the password is hashed.

- [ ] **3. Give `UserService` the email sender.** Change the constructor to `UserService(userRepo, hasher, emailService: EmailService, templateFactory: AuthEmailTemplateFactory)`.

- [ ] **4. Send a confirmation in `registerUser(email, password, firstName, lastName) -> User`.**
  - After the user is saved, call `emailService.sendEmail(user.email, "Your scheduler account", templateFactory.buildConfirmationEmail(user.firstName, user.email))`.
  - If that raises `MailDeliveryError`, keep the account and raise a new `MailDeliveryError(f"Account {userId} was created but the confirmation email was not sent")`.
  - Otherwise return the saved `User`.

- [ ] **5. Fix `UserService`'s opening comment.** It says the service does not send mail. Change that sentence.

- [ ] **6. Add `SessionManager.removeSessionsForUser(userId) -> None`** in `scheduler/infrastructure/session_manager.py`. Remove every in-memory session whose `userId` matches.

- [ ] **7. Create `scheduler/controllers/user_controller.py` with class `UserController`.**
  - Constructor: `UserController(userService, authService, sessionManager)`.
  - Every handler is `return respond(lambda: ...)`.

- [ ] **8. Add `handleRegisterUser(request) -> Response`.**
  - No session check.
  - Reads `email`, `password`, `firstName`, `lastName` from `request`.
  - Calls `registerUser`. `data` = public user dict `{userId, email, firstName, lastName, allowEmailReminders}`.

- [ ] **9. Add `handleUpdateProfile(request) -> Response`.**
  - `session = authService.requireSession(request.get("token"))`.
  - Calls `updateProfileData(session.userId, request["email"], request["firstName"], request["lastName"])`. `data` = `None`.

- [ ] **10. Add `handleDeleteAccount(request) -> Response`.**
  - `requireSession`, then `deleteUserAccount(session.userId, request["password"])`, then `sessionManager.removeSessionsForUser(session.userId)`. `data` = `None`.

- [ ] **11. Wire it in `scheduler/application.py`.** Build `UserService` with the new arguments, create `UserController(userService, authService, sessionManager)`, and set `app.userController`.

### Test it

On `buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="console")`:

1. Register `ada@ilstu.edu` / `secret12`: `ok`, no `passwordHash` in `data`, a confirmation is printed.
2. Register `ada@gmail.com`: `invalid`, message `Email must end with @ilstu.edu`.
3. Register with password `short`: `invalid`. Register the same email twice: `invalid`.
4. Update profile with a login token: `ok`. Without a token: `unauthenticated`.
5. Delete with the wrong password: `forbidden`. With the right password: `ok`, and the old token now gives `unauthenticated`.

### Do not

- Add a profile description or a password change to the profile update.
- Check the password in the controller. The service does it.
- Delete the user's groups, invitations, meetings, or files.

## D1-6: Log in and log out (issue #9)

**Goal:** Let a student log in with email and password, and log out.

**Start after:** K2 (#4) and D1-1 (#3).

### Steps

- [ ] **1. Create `scheduler/controllers/auth_controller.py` with class `AuthController`.**
  - Constructor: `AuthController(authService)`.

- [ ] **2. Add `handleLogin(request) -> Response`.**
  - No session check.
  - Reads `email` and `password`, calls `authService.login(email, password)`.
  - `data` = `{userSessionId, userId, token, loginTime, expiryTime}` from the returned `UserSession`.
  - A wrong email or password already raises `PermissionError("Invalid email or password")` in the service, so the status is `forbidden`. Do not say which one was wrong.

- [ ] **3. Add `handleLogout(request) -> Response`.**
  - `session = authService.requireSession(request.get("token"))`, then `authService.logout(session.token)`. `data` = `None`.

- [ ] **4. Wire it in `scheduler/application.py`.** Set `app.authController = AuthController(authService)`.

### Test it

1. Register a user, then `handleLogin` with the right password: `ok` and `data["token"]` is set.
2. Wrong password: `forbidden`, message `Invalid email or password`.
3. `handleLogout({"token": token})`: `ok`. The same call again: `unauthenticated`, `Session is not active`.

### Do not

- Check the password in the controller.
- Add a "refresh session" handler or a second login step.

## D1-7: Forgot password and reset password (issue #10)

**Goal:** Add the "Forgot password" and "Set a new password" actions, using the service from D1-4.

**Start after:** K2 (#4) and D1-4 (#7).

### Steps

- [ ] **1. Create `scheduler/controllers/password_recovery_controller.py` with class `PasswordRecoveryController`.**
  - Constructor: `PasswordRecoveryController(recoveryService)`.
  - Neither handler checks a session.

- [ ] **2. Add `handleForgotPassword(request) -> Response`.**
  - No `email` key: return `Response(Response.INVALID, message="Email is required")`.
  - Otherwise call `recoveryService.requestResetLink(request["email"])` and return `ok` with this exact message, whatever happened:

    ```text
    If an account exists for that email, a reset link has been sent.
    ```

- [ ] **3. Add `handleResetPassword(request) -> Response`.**
  - Reads `token` and `newPassword`, calls `recoveryService.completePasswordReset(token, newPassword)`. `data` = `None`.
  - Errors map through `respond`: bad token or weak password is `invalid`; deleted user is `notFound`.

- [ ] **4. Wire it in `scheduler/application.py`.** Set `app.passwordRecoveryController = PasswordRecoveryController(passwordRecoveryService)`.

### Test it

With `mailHost="console"`:

1. Forgot-password for an unknown email and for a real user return the same `Response`.
2. Reset with the printed token and `newpass1`: `ok`. Logging in with the old password fails; `newpass1` works.
3. Reset with a login token: `invalid`, `Invalid or expired token`.

### Do not

- Read or decode the token in the controller.
- Create a session after a reset.

## N1: Daily database backup (issue #32)

**Goal:** Make a dated copy of the database file once a day, so data can be restored if something breaks.

**Start after:** K1 (#2).

### Steps

- [ ] **1. Create `scheduler/infrastructure/backup.py`.** Its opening comment says:
  - An operator runs this once a day.
  - It works on the DuckDB database file.
  - To restore, copy the backup back to the path `DuckDBConnection` opens.

- [ ] **2. Add the function `backupDatabase(sourcePath, destinationDirectory) -> str`.**
  1. If `sourcePath` does not exist, raise `FileNotFoundError`.
  2. Create `destinationDirectory` if needed.
  3. Copy the file to `{destinationDirectory}/{original name without extension}-{YYYY-MM-DD}{extension}`, using today's UTC date. Running it twice on the same day overwrites that day's copy.
  4. Return the path of the copy.

### Test it

1. Create a small DuckDB file, call `backupDatabase`, and check the destination has a same-size copy with today's UTC date in its name.
2. Call it with a path that does not exist: `FileNotFoundError`.

### Do not

- Call it from `buildApplication` or start a backup thread.
- Go through `Database` or add a backup table.
