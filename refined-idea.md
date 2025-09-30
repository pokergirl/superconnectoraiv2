**App Description**: An admin-assisted password reset feature designed for simplicity and security. The process is initiated manually by the user, who emails a designated admin outside of the application. The admin then uses an enhanced UI to securely generate and send a One-Time Passcode (OTP) to the user.

**Target Users**: Existing application users who have forgotten their password and the application administrator.

**Core Features**:
1.  **User-Facing Prompt**: A "Forgot Password" link displays the message: "Please email your password reset request to ha@nextstepfwd.com from the email you registered with. An administrator will send you a One-Time Passcode."
2.  **Admin-Initiated Workflow**: After receiving the user's email, the admin navigates to the Access Requests page.
3.  **Enhanced Admin UI**: The Access Requests page will include a search/filter bar, allowing the admin to find the user by their email address.
4.  **One-Click Reset & Email**: The admin clicks a **"Reset Password"** button for the correct user, which:
    *   Generates a secure, single-use One-Time Passcode (OTP).
    *   Opens a pre-filled email template containing instructions for the user and the OTP.
5.  **Admin Sends Email**: The admin reviews and sends the email to the user to complete the process.

**Technical Requirements**:
*   UI enhancement on the Access Requests page to include a search/filter component.
*   A service to generate and manage the lifecycle of secure OTPs.
*   An email composition modal/template that is populated with the user's email and the generated OTP.