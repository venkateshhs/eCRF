# Case-e Documentation 

## eCRF – Electronic Case Report Form System

**Introduction:**  
Case-e is a web-based **Electronic Case Report Form** system designed to capture and manage clinical trial data digitally. It provides a user friendly platform for researchers, clinicians and data managers to collect participant data, manage studies, and maintain data quality in clinical trials. By replacing traditional paper forms with eCRF, the system helps reduce errors, enforce data validation, provides data versioning and streamline the workflow of clinical data capture.

### Features  
- **Study Management:** Organize clinical trials with the ability to create and manage studies. Each study can contain multiple forms (CRFs) corresponding to different visits, subjects and subject groups.  
- **Form Design and Data Capture:** Design electronic case report forms for capturing a variety of data points (e.g., patient demographics, lab results, adverse events). The forms support standard, custom field types (text, numeric, dates, dropdowns, etc.) and can include validation rules to ensure data quality.  
- **User Management and Roles:** eCRF supports multiple user accounts with role-based access. An **Admin** user can add or remove users and assign roles (such as Investigators, Principal Investigator and Viewer). This ensures that each user sees and edits only the data they are authorized to handle.  
- **Data Validation and Quality Control:** Built-in validation rules and checks can be configured for form fields (for example, range checks for numeric values or required fields). This helps catch data entry errors in real-time while submitting data. 
- **Audit Trail:** For compliance with clinical research regulations, eCRF maintains an audit trail of changes. Any modifications to data entries (like updates or deletions) are logged with user, time, and details, ensuring data integrity and traceability.  
- **Data Export:** Collected data can be exported for analysis or reporting. eCRF provides options to export study data in common formats (e.g., CSV or Excel) so that researchers can analyze the results outside the system.  
- **Secure Access:** The application requires user authentication. All users have unique logins, and sensitive actions are restricted to authorized roles. By default, an administrator account is provided (details below), and all users are encouraged to use strong passwords and keep their credentials secure.

### Installation and Setup (Source Version)  
The standalone, exxecutable eCRF application can be obtained from the source repository (https://github.com/venkateshhs/case-e). 

### Usage  
Once the eCRF application is running, you can access its user interface through a web browser or the provided application window:

- **Accessing the Application:** If you started eCRF on a local server, open your web browser and navigate to : http://127.0.0.1:8000/login . If you are using the standalone **case-e** application, launching it will either open a built-in window or start a local service and open a browser automatically.  
- **Logging In:** Use the default administrator account to log in for the first time. The default credentials are **Username:** `admin` and **Password:** `Admin123!`.  After entering these on the login screen, you will gain access to the system as an administrator.  
- **Post-Login Setup:** After logging in, it is **strongly recommended to change the default password** for security. Navigate to the **User Management** section of the application. There you can change the password for the admin account (`admin`) and add other user accounts. Always ensure that the admin password is updated from the default, especially if the system is deployed in a production or shared environment.  
- **Creating Studies and Forms:** As an admin or user with the appropriate role, you can create a new study and then design the case report forms for that study. Define the fields for each form and any validation rules. Once forms are set up, they become available for data entry.  
- **Data Entry:** Users with data entry privileges can enter participant data into the eCRF forms per subject per visit. Typically, you would select a study (and a subject) and fill out the forms for each visit. The system will enforce any field validations and will provide instant feedback if data doesn’t meet the specified criteria (for example, an out-of-range value).  
- **Saving and Editing Data:** After entering data on a form, save the form. Saved data can later be edited by authorized users. Thanks to the audit trail, any changes are tracked. Saved data for study can be viewd in Study Dashboard.
- **User Management and Roles:** Through the User Management interface, the admin can create new users (e.g., for Investigators, Principal Investigator and Viewer) and assign them roles. Roles control what each user can do in the system. For instance, a **Investigators** role might only allow entering and viewing data, while an **Admin** role can design forms and manage users. Always grant the least privileges necessary for each user to maintain data security.  
- **Data Export:** When you need to analyze data, use the export functionality to download the dataset. This will  produce a CSV or spreadsheet of all collected data, which you can then use for statistical analysis or reporting.

By leveraging these features, eCRF makes it easier to conduct clinical trials and research studies by ensuring data is collected consistently and securely.
