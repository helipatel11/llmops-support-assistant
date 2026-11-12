# Spot check: v1

You are checking whether the automatic judge scores answers the way a person would.
For each question below, read it, then write two numbers in
`evaluation/results/spot_check_v1_scores.csv` on the line with the same id.

**grounded**: is everything the answer says supported by the "Context given to the model"?
- `1` = every claim can be found in the context (missing things is fine here)
- `0` = it says at least one thing the context does not support (invented step, wrong number)

**correct**: does the answer contain the "Facts a correct answer must contain"?
- `2` = all of them, nothing contradicting
- `1` = some of them
- `0` = none of them, a contradiction, or it declined to answer

**If the answer declines** ("the context does not mention...", "I could not find..."),
write `1` for grounded and `0` for correct.

Example line in the scores file, for an answer that is supported but misses a fact:
`q12,1,1`

Score on your own first; the judge's scores are not in this file on purpose.

---

## q01: How long is a password reset link good for?

**Facts a correct answer must contain:**
- the link expires after 30 minutes

**Context given to the model:**

> Password Reset
>
> Users can reset their own password from the "Forgot password" link on the sign-in page. A reset link is emailed to the registered work address and expires after 30 minutes.
>
> If the reset email does not arrive within 5 minutes:
> - check the spam or junk folder
> - confirm the registered email address in the HR portal
> - request a new link (only the most recent link works)
> - contact the support team if it still has not arrived
>
> Account Lockout
>
> An account is locked automatically after 5 failed sign-in attempts in a row. The lock lasts 15 minutes and then clears by itself; you do not need to contact support for a single lockout.
>
> If your account locks again straight after unlocking, an old password is probably saved somewhere and retrying in the background. Common sources are a phone mail app, a mapped network drive, or the VPN client. Update or remove the saved password on each device.

**Model's answer:**

> The provided context does not mention the length of a password reset link. The answer is not present in the context, and it is not mentioned in the given context.

Write in the scores file: `q01,<grounded>,<correct>`

---

## q03: How many wrong password attempts before I get locked out, and for how long?

**Facts a correct answer must contain:**
- locked after 5 failed attempts
- the lock lasts 15 minutes

**Context given to the model:**

> Account Lockout
>
> An account is locked automatically after 5 failed sign-in attempts in a row. The lock lasts 15 minutes and then clears by itself; you do not need to contact support for a single lockout.
>
> If your account locks again straight after unlocking, an old password is probably saved somewhere and retrying in the background. Common sources are a phone mail app, a mapped network drive, or the VPN client. Update or remove the saved password on each device.
>
> Password rules: at least 12 characters, not one of your last 5 passwords. Passwords expire every 180 days and you are reminded by email 14 days before expiry.
>
> Support staff will never ask for your password. Do not share it in tickets, chat or email.

**Model's answer:**

> The context provided does not mention any information about the number of wrong password attempts before being locked out, or the length of the lockout. The answer provided is based on the knowledge base information provided.

Write in the scores file: `q03,<grounded>,<correct>`

---

## q04: My account keeps getting locked again right after it unlocks. Why?

**Facts a correct answer must contain:**
- an old saved password keeps retrying
- update or remove the saved password on each device

**Context given to the model:**

> Account Lockout
>
> An account is locked automatically after 5 failed sign-in attempts in a row. The lock lasts 15 minutes and then clears by itself; you do not need to contact support for a single lockout.
>
> If your account locks again straight after unlocking, an old password is probably saved somewhere and retrying in the background. Common sources are a phone mail app, a mapped network drive, or the VPN client. Update or remove the saved password on each device.
>
> To unlock immediately, call the service desk and verify your identity with your employee ID and manager's name. The service desk cannot unlock accounts by email.
>
> Repeated lockouts from unknown locations are treated as a possible security incident and reported to the security team.

**Model's answer:**

> The provided context states that if your account is locked again after unlocking, an old password is probably saved on your device(s) and retrieving it in the background. Common sources of saved passwords include phone mail apps, mapped network drives, or VPN clients. To unlock immediately, call the service desk and verify your identity with your employee ID and manager's name. The service desk cannot unlock accounts by email. The repeated lockouts from unknown locations are treated as a possible security incident and reported to the security team.

Write in the scores file: `q04,<grounded>,<correct>`

---

## q05: I'm getting a new phone. How do I move my authenticator?

**Facts a correct answer must contain:**
- move MFA to the new phone in the security portal before wiping the old one
- if the old phone is gone, the service desk can issue a bypass code

**Context given to the model:**

> New phone: before wiping the old phone, open the security portal and move MFA to the new device. If the old phone is lost or already wiped, the service desk can issue a one-time bypass code valid for 24 hours after identity verification.
>
> Codes are time-based. If codes are always rejected, check that the phone's clock is set automatically.
>
> Multi-Factor Authentication (MFA)
>
> MFA is required for all staff accounts. The supported method is the Authenticator app on a phone; SMS codes are only allowed as a temporary fallback for up to 7 days.
>
> To set up MFA, sign in to the security portal, choose "Add method", and scan the QR code with the Authenticator app. Enter the 6-digit code to confirm.

**Model's answer:**

> To move your authenticator to the new phone, follow these steps:
>
> 1. Log in to the security portal on the new phone.
> 2. Click on "Add method" and select "Authenticator app."
> 3. Scan the QR code with the Authenticator app on the old phone.
> 4. Enter the 6-digit code to confirm the move.
>
> If the authenticator is not working on the new phone, check that the phone's clock is set automatically. If the phone is still not working, contact the IT support team for assistance.

Write in the scores file: `q05,<grounded>,<correct>`

---

## q08: The login page keeps bouncing me back and forth and never loads. Fix?

**Facts a correct answer must contain:**
- clear cookies
- try a private browser window
- check the computer clock

**Context given to the model:**

> Single Sign-On (SSO) Login Errors
>
> Most internal applications use single sign-on. If an application shows "Access denied" after signing in, your account has not been assigned to that application. Ask your manager to request access through the access request form; approval usually takes one business day.
>
> If you see a redirect loop (the page keeps reloading between the app and the sign-in page):
> - clear cookies for the application and the sign-in domain
> - try a private browser window
> - make sure the computer clock is correct; SSO tokens fail if the clock is off by more than 5 minutes
>
> The error "AADSTS50076" means MFA is required but was not completed. Sign out completely and sign in again, approving the MFA prompt.

**Model's answer:**

> If the login page keeps bouncing you back and forth and never loads, it could be due to a redirect loop. Clear cookies for the application and the sign-in domain, try a private browser window, make sure the computer clock is correct, and SSO tokens fail if the clock is off by more than 5 minutes. The error "AADSTS50076" means MFA is required but was not completed. Sign out completely and sign in again, approving the MFA prompt.

Write in the scores file: `q08,<grounded>,<correct>`

---

## q09: Which VPN client version do I need?

**Facts a correct answer must contain:**
- version 5.2 or newer

**Context given to the model:**

> VPN Troubleshooting
>
> The company VPN is required to reach internal systems from outside the office. It is not needed in the office.
>
> If the VPN connection fails:
> - check that your internet connection works without the VPN
> - quit and restart the VPN client
> - sign in with your company credentials, not a personal account
> - make sure the client is version 5.2 or newer; older versions are blocked
>
> If the VPN connects but internal sites do not load, disconnect, flush DNS (ipconfig /flushdns on Windows, or restart the laptop), and reconnect.
>
> The VPN disconnects automatically after 12 hours, even if you are active. Reconnect to continue. Hotel and airport networks sometimes block the VPN; use a phone hotspot as a workaround.

**Model's answer:**

> The context provided does not mention which VPN client version you need. The answer is not present in the context, and it is recommended to check the knowledge base for more information.

Write in the scores file: `q09,<grounded>,<correct>`

---

## q14: How do I get access to the team's shared inbox?

**Facts a correct answer must contain:**
- a manager requests it through the access request form
- access appears within 2 hours of approval

**Context given to the model:**

> Shared Drive Access
>
> Access to shared drives and team folders is controlled by the folder owner. Request access through the access request form and name the folder path; the owner approves it, normally within one business day.
>
> If access was approved but the folder is still missing, sign out and sign in again, or reconnect to the VPN when working remotely.
>
> Access to team systems is not automatic; the manager requests it through the access request form.
>
> Leavers: managers submit the leaver form before the last day. Accounts are disabled at 6pm on the last working day and the laptop must be returned the same day.

**Model's answer:**

> If you are an IT support assistant, the answer to your question is that you cannot get access to the team's shared inbox. The folder owner (the team's manager) must approve your access request through the access request form and name the folder path. If the folder is still missing, you can sign out and sign in again, or reconnected to the VPN when working remotely. Access to team systems is not automatic, and the manager must request it through the access request form before the last day. The laptop must be returned the same day.

Write in the scores file: `q14,<grounded>,<correct>`

---

## q21: How long until a customer sees their refund?

**Facts a correct answer must contain:**
- 5 to 10 business days

**Context given to the model:**

> Refunds
>
> Customers can request a full refund within 30 days of purchase. After 30 days, refunds are only given for duplicate charges or service outages.
>
> Refunds are issued to the original payment method. They appear on the customer's statement within 5 to 10 business days, depending on the bank.
>
> Support agents can approve refunds up to 200 dollars. Larger refunds need approval from a team lead.
>
> For duplicate charges, check the payment service for two successful transactions with the same order ID before refunding. A pending authorisation is not a charge and drops off automatically within 7 days.

**Model's answer:**

> The provided context does not mention how long a customer will see their refund. The answer provided is based on the information provided in the knowledge base.

Write in the scores file: `q21,<grounded>,<correct>`

---

## q24: How quickly must we respond to a Sev2?

**Facts a correct answer must contain:**
- within 1 hour
- during business hours

**Context given to the model:**

> Sev4 (request): questions, cosmetic issues and feature suggestions. Response within 3 business days.
>
> When unsure, choose the higher severity; it can be lowered later.
>
> Incident Severity Levels
>
> Sev1 (critical): a production service is down or most customers are affected, for example payments failing or a full outage. Response within 15 minutes, 24/7, and the on-call engineer is paged.
>
> Sev2 (major): a service is degraded or a subset of customers is affected and there is no good workaround. Response within 1 hour during business hours.
>
> Sev3 (minor): a single user is affected, or there is a workaround. Response within 1 business day.

**Model's answer:**

> If the Sev2 severity level is reached, the response time is 1 hour during business hours.

Write in the scores file: `q24,<grounded>,<correct>`

---

## q25: When should a manager request accounts for someone joining the team?

**Facts a correct answer must contain:**
- at least 5 business days before the start date
- using the new starter form

**Context given to the model:**

> New Starter Onboarding
>
> Managers request accounts for new starters at least 5 business days before the start date using the new starter form. Late requests may mean the person has no laptop on day one.
>
> On day one the new starter collects their laptop and badge from the service desk, signs in with the temporary password from their manager, and is asked to set a new password and set up MFA immediately.
>
> Access to team systems is not automatic; the manager requests it through the access request form.
>
> Leavers: managers submit the leaver form before the last day. Accounts are disabled at 6pm on the last working day and the laptop must be returned the same day.

**Model's answer:**

> When should a manager request accounts for someone joining the team?
>
> Answer:
> The manager should request accounts for new starters at least 5 business days before the start date using the new starter form. Late requests may mean the person has no laptop on day one, and on day one the new starter collects their laptop and badge from the service desk, signs in with the temporary password from their manager, and is asked to set a new password and set up MFA immediately. Access to team systems is not automatic; the manager requests it through the access request form.

Write in the scores file: `q25,<grounded>,<correct>`

---
