from ecrf_backend.auth import verify_password

plaintext_password = "Password123!"
hashed_password = "$2b$12$Qu3Y/0gDlH.L/sWnTKgBTe3Pq1ZwSO8VAXsfhelZMTc/SshVtPfCW"  # Replace with hash from database

print("Password Verified:", verify_password(plaintext_password, hashed_password))
