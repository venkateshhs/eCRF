# eCRF Platform

This project is an **Electronic Case Report Form (eCRF) Platform** designed for dynamic form creation, management, and data collection. The platform leverages modern web technologies like **Vue.js** for the frontend and **FastAPI** for the backend. It supports SHACL-based templates to enable flexible form generation and validation.

## Features Implemented

### 1. **User Authentication**
- **Registration**: Users can register with their username, email, and password.
- **Login**: Supports user login with JWT-based authentication.
- **Password Management**: Users can change their password, with validations like requiring a mix of characters and preventing reuse of old passwords.

### 2. **Dynamic Form Creation**
- **SHACL-Based Templates**: Forms are created dynamically based on SHACL templates loaded from JSON files.
- **Template Selection**: Users can select from available SHACL templates.
- **Customizable Fields**: 
  - Add a similar field.
  - Edit an existing field's label.
  - Delete an unwanted field.

### 3. **Form Validation**
- **Field-Level Validations**:
  - `Age`: Must be between 0 and 120, calculated dynamically if `DOB` is provided.
  - `DOB`: Prevents future dates.
  - `Text Fields`: Default maximum length of 255 characters.
  - `Heart Rate`: Range validation between 30 bpm and 200 bpm.
  - `Blood Group`: Dropdown with predefined options.
- Validations are enforced dynamically while rendering the forms.
- **Validations are not yet working**

### 4. **Responsive Frontend**
- Built using Vue.js with:
  - **Dynamic Form Components**: Automatically render fields based on SHACL templates.
  - **Interactive User Interface**:
    - Simple and consistent buttons with icons (edit, delete, add).
    - Real-time validation feedback.
  - **Template Rendering**: Select a template and dynamically load the fields.

### 5. **Backend Features**
- **FastAPI**: Provides REST APIs for authentication, template loading, and form data management.
- **SHACL Templates**:
  - Templates are stored in the `shacl/templates` directory as JSON files.
  - APIs to list all templates and load a specific template.
- **Dynamic Form Persistence**:
  - Yet to do: saving of forms and reloading with data.



