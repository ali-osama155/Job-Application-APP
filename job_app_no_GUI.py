import pyodbc
from datetime import datetime, timedelta
import uuid

# Database connection configuration
CONN_STR = (
    r"DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=ALIOSAMA155\SQLEXPRESS;"
    r"DATABASE=my_project;"
    r"Trusted_Connection=Yes;"
)

# Global variables
logged_in_user = None

def get_connection():
    """Establish database connection with error handling"""
    try:
        conn = pyodbc.connect(CONN_STR)
        return conn
    except Exception as e:
        print(f"Connection Error: Failed to connect to database: {str(e)}")
        return None

# ─── Authentication Functions ───────────────────────────────────────────
def login():
    global logged_in_user
    email = input("Enter Email: ").strip()
    password = input("Enter Password: ").strip()

    if not email or "@" not in email or "." not in email:
        print("Login Error: Invalid email format! Must contain '@' and '.'")
        return False
    if len(password) < 6:
        print("Login Error: Password must be at least 6 characters!")
        return False

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT UserID, Name, Email, Role 
                FROM [User] 
                WHERE Email = ? AND Password = ?
            """, (email, password))
            user = cursor.fetchone()
            if user:
                user_info = {
                    'user_id': user.UserID,
                    'name': user.Name,
                    'email': user.Email,
                    'role': 'Employer' if user.Role == 0 else 'JobSeeker'
                }
                if user.Role == 0:
                    cursor.execute(
                        "SELECT ComName FROM Employer WHERE UserID = ?", user.UserID)
                    employer_info = cursor.fetchone()
                    user_info['company_name'] = employer_info.ComName if employer_info else None
                logged_in_user = user_info
                print(f"Login successful! Welcome {user_info['name']}")
                return True
            else:
                print("Login Error: Invalid email or password")
                return False
        except Exception as e:
            print(f"Login Error: Login failed: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

def register_user():
    name = input("Enter Name: ").strip()
    email = input("Enter Email: ").strip()
    phone = input("Enter Phone: ").strip()
    role = input("Enter Role (Employer/JobSeeker): ").strip().capitalize()
    password = input("Enter Password: ").strip()

    if not name:
        print("Error: Name cannot be empty!")
        return
    if not email or "@" not in email or "." not in email:
        print("Error: Invalid email format! Must contain '@' and '.'")
        return
    if not phone.isdigit():
        print("Error: Phone must be digits only!")
        return
    if role not in ["Employer", "JobSeeker"]:
        print("Error: Role must be 'Employer' or 'JobSeeker'!")
        return
    if len(password) < 6:
        print("Error: Password must be at least 6 characters!")
        return

    role_num = 0 if role == "Employer" else 1
    if role == "Employer":
        company_name = input("Enter Company Name: ").strip()
        industry = input("Enter Industry: ").strip()
        location = input("Enter Location: ").strip()
        if not all([company_name, industry, location]):
            print("Error: All Employer fields are required!")
            return
        kwargs = {"company_name": company_name, "industry": industry, "location": location}
    else:
        resume_link = input("Enter Resume Link: ").strip()
        industry = input("Enter Preferred Industry: ").strip()
        location = input("Enter Preferred Location: ").strip()
        if not all([resume_link, industry, location]):
            print("Error: All JobSeeker fields are required!")
            return
        kwargs = {"resume_link": resume_link, "industry": industry, "location": location}

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO [User] (Name, Email, Phone, Role, Password)
                OUTPUT INSERTED.UserID
                VALUES (?, ?, ?, ?, ?)
            """, name, email, phone, role_num, password)
            user_id = cursor.fetchone().UserID

            if role == "Employer":
                cursor.execute("""
                    INSERT INTO Employer (UserID, ComName, ComIndustry, Location, AnnouncedJobCount)
                    VALUES (?, ?, ?, ?, 0)
                """, user_id, kwargs["company_name"], kwargs["industry"], kwargs["location"])
            else:
                cursor.execute("""
                    INSERT INTO JobSeeker (UserID, ResumeLink, Industry, PreferredLocation, AppliedJobCount)
                    VALUES (?, ?, ?, ?, 0)
                """, user_id, kwargs["resume_link"], kwargs["industry"], kwargs["location"])

            conn.commit()
            print(f"User registered successfully! UserID: {user_id}")
        except pyodbc.IntegrityError:
            print("Error: Email already exists!")
        except Exception as e:
            conn.rollback()
            print(f"Error: Failed to register user: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def logout():
    global logged_in_user
    logged_in_user = None
    print("Logged out successfully!")

# ─── Job Management Functions ──────────────────────────────────────────
def create_job():
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        print("Error: You must be logged in as an Employer to create a job!")
        return
    title = input("Enter Job Title: ").strip()
    desc = input("Enter Description: ").strip()
    industry = input("Enter Industry: ").strip()
    location = input("Enter Location: ").strip()
    skills = input("Enter Required Skills: ").strip()
    exp_input = input("Enter Minimum Experience (years): ").strip()
    
    if not exp_input:
        print("Error: Minimum experience is required!")
        return
    try:
        exp = int(exp_input)
        if exp < 0:
            print("Error: Experience cannot be negative!")
            return
    except ValueError:
        print("Error: Minimum experience must be a valid number!")
        return
    if not all([title, desc, industry, location, skills]):
        print("Error: All fields are required!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO VacancyJob (EmployerID, Title, Description, Industry, Location, ReqSkill, EXPRequired, AppCount, Status)
                OUTPUT INSERTED.JobID
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'Open')
            """, logged_in_user['user_id'], title, desc, industry, location, skills, exp)
            job_id = cursor.fetchone().JobID
            cursor.execute("UPDATE Employer SET AnnouncedJobCount = AnnouncedJobCount + 1 WHERE UserID = ?", logged_in_user['user_id'])
            conn.commit()
            print(f"Job created successfully! JobID: {job_id}")
        except Exception as e:
            conn.rollback()
            print(f"Error: Failed to create job: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def hide_job():
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        print("Error: You must be logged in as an Employer to hide a job!")
        return
    job_id_input = input("Enter Job ID: ").strip()
    if not job_id_input:
        print("Error: Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        print("Error: Job ID must be a valid number!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT JobID FROM VacancyJob WHERE JobID = ? AND EmployerID = ?", job_id, logged_in_user['user_id'])
            job = cursor.fetchone()
            if not job:
                print(f"Error: No job found with JobID: {job_id} for this Employer!")
                return
            cursor.execute("UPDATE VacancyJob SET Status = 'Closed' WHERE JobID = ?", job_id)
            conn.commit()
            print(f"JobID: {job_id} has been hidden successfully")
        except Exception as e:
            conn.rollback()
            print(f"Error: Hide error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def delete_job():
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        print("Error: You must be logged in as an Employer to delete a job!")
        return
    job_id_input = input("Enter Job ID: ").strip()
    if not job_id_input:
        print("Error: Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        print("Error: Job ID must be a valid number!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT EmployerID FROM VacancyJob WHERE JobID = ?", job_id)
            job = cursor.fetchone()
            if not job:
                print(f"Error: No job found with JobID: {job_id}")
                return
            if job.EmployerID != logged_in_user['user_id']:
                print("Error: You can only delete jobs that you created!")
                return
            cursor.execute("DELETE FROM Application WHERE JobID = ?", job_id)
            cursor.execute("DELETE FROM SavedVacancy WHERE JobID = ?", job_id)
            cursor.execute("DELETE FROM VacancyJob WHERE JobID = ?", job_id)
            cursor.execute("UPDATE Employer SET AnnouncedJobCount = AnnouncedJobCount - 1 WHERE UserID = ?",
                           logged_in_user['user_id'])
            conn.commit()
            print(f"Deleted job with JobID: {job_id}")
        except Exception as e:
            conn.rollback()
            print(f"Error: Delete error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def apply_for_job():
    if not logged_in_user or logged_in_user['role'] != 'JobSeeker':
        print("Error: You must be logged in as a JobSeeker to apply for a job!")
        return
    job_id_input = input("Enter Job ID: ").strip()
    if not job_id_input:
        print("Error: Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        print("Error: Job ID must be a valid number!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT Status FROM VacancyJob WHERE JobID = ?", job_id)
            job = cursor.fetchone()
            if not job:
                print(f"Error: No job found with JobID: {job_id}")
                return
            if job.Status != 'Open':
                print("Error: This job is not open for applications!")
                return
            cursor.execute("SELECT AppID FROM Application WHERE SeekerID = ? AND JobID = ?",
                           logged_in_user['user_id'], job_id)
            if cursor.fetchone():
                print("Error: You have already applied for this job!")
                return
            cursor.execute("INSERT INTO Application (JobID, SeekerID, Status, ApplyDate) VALUES (?, ?, 'Pending', ?)",
                           job_id, logged_in_user['user_id'], datetime.now().date())
            cursor.execute("UPDATE VacancyJob SET AppCount = AppCount + 1 WHERE JobID = ?", job_id)
            cursor.execute("UPDATE JobSeeker SET AppliedJobCount = AppliedJobCount + 1 WHERE UserID = ?", logged_in_user['user_id'])
            conn.commit()
            print(f"Successfully applied for JobID: {job_id}")
        except Exception as e:
            conn.rollback()
            print(f"Error: Apply error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def save_job():
    if not logged_in_user or logged_in_user['role'] != 'JobSeeker':
        print("Error: You must be logged in as a JobSeeker to save a job!")
        return
    job_id_input = input("Enter Job ID: ").strip()
    if not job_id_input:
        print("Error: Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        print("Error: Job ID must be a valid number!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT Status FROM VacancyJob WHERE JobID = ?", job_id)
            job = cursor.fetchone()
            if not job:
                print(f"Error: No job found with JobID: {job_id}")
                return
            if job.Status != 'Open':
                print("Error: This job is not open and cannot be saved!")
                return
            cursor.execute("SELECT JobID FROM SavedVacancy WHERE SeekerID = ? AND JobID = ?",
                           logged_in_user['user_id'], job_id)
            if cursor.fetchone():
                print("Error: You have already saved this job!")
                return
            cursor.execute("INSERT INTO SavedVacancy (JobID, SeekerID, SaveDate) VALUES (?, ?, ?)",
                           job_id, logged_in_user['user_id'], datetime.now().date())
            conn.commit()
            print(f"Successfully saved JobID: {job_id}")
        except Exception as e:
            conn.rollback()
            print(f"Error: Save error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def accept_application():
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        print("Error: You must be logged in as an Employer to accept applications!")
        return
    app_id = input("Enter Application ID: ").strip()
    if not app_id:
        print("Error: Application ID is required!")
        return
    try:
        app_id = int(app_id)
    except ValueError:
        print("Error: Application ID must be a valid number!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Application SET Status = 'Accepted' WHERE AppID = ?", app_id)
            conn.commit()
            print(f"Application status updated to Accepted for AppID: {app_id}")
        except Exception as e:
            conn.rollback()
            print(f"Error: Update error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def reject_application():
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        print("Error: You must be logged in as an Employer to reject applications!")
        return
    app_id = input("Enter Application ID: ").strip()
    if not app_id:
        print("Error: Application ID is required!")
        return
    try:
        app_id = int(app_id)
    except ValueError:
        print("Error: Application ID must be a valid number!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Application SET Status = 'Rejected' WHERE AppID = ?", app_id)
            conn.commit()
            print(f"Application status updated to Rejected for AppID: {app_id}")
        except Exception as e:
            conn.rollback()
            print(f"Error: Update error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def list_jobs():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT v.JobID, v.Title, v.Location, e.ComName, e.ComIndustry
                FROM VacancyJob v
                JOIN Employer e ON v.EmployerID = e.UserID
                WHERE v.Status = 'Open'
            """)
            rows = cursor.fetchall()
            if rows:
                print("\nOpen Jobs:")
                for row in rows:
                    print(f"JobID: {row.JobID}, Title: {row.Title}, Location: {row.Location}, "
                          f"Company: {row.ComName}, Industry: {row.ComIndustry}")
            else:
                print("No open jobs found.")
        except Exception as e:
            print(f"Error: Select error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def list_saved_jobs():
    if not logged_in_user or logged_in_user['role'] != 'JobSeeker':
        print("Error: You must be logged in as a JobSeeker to view saved jobs!")
        return
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT sv.JobID, v.Title, v.Description, v.Industry, v.Location
                FROM SavedVacancy sv
                JOIN VacancyJob v ON sv.JobID = v.JobID
                WHERE sv.SeekerID = ?
            """, logged_in_user['user_id'])
            rows = cursor.fetchall()
            if rows:
                print("\nSaved Jobs:")
                for row in rows:
                    print(f"JobID: {row.JobID}, Title: {row.Title}, Description: {row.Description}, "
                          f"Industry: {row.Industry}, Location: {row.Location}")
            else:
                print("No saved jobs found.")
        except Exception as e:
            print(f"Error: Select error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def list_applications():
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        print("Error: You must be logged in as an Employer to view applications!")
        return
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT a.AppID, a.JobID, v.Title, u.Name, a.Status
                FROM Application a
                JOIN VacancyJob v ON a.JobID = v.JobID
                JOIN [User] u ON a.SeekerID = u.UserID
                WHERE v.EmployerID = ?
            """, logged_in_user['user_id'])
            rows = cursor.fetchall()
            if rows:
                print("\nApplications:")
                for row in rows:
                    print(f"AppID: {row.AppID}, JobID: {row.JobID}, Job Title: {row.Title}, "
                          f"Seeker Name: {row.Name}, Status: {row.Status}")
            else:
                print("No applications found.")
        except Exception as e:
            print(f"Error: Select error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def filter_vacancies():
    industry = input("Enter Industry (or press Enter to skip): ").strip() or None
    location = input("Enter Location (or press Enter to skip): ").strip() or None
    exp_input = input("Enter Maximum Experience (or press Enter to skip): ").strip() or None
    if exp_input:
        try:
            exp = int(exp_input)
            if exp < 0:
                print("Error: Experience cannot be negative!")
                return
        except ValueError:
            print("Error: Maximum experience must be a valid number!")
            return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            conditions = []
            values = []
            query = """
                SELECT v.JobID, v.Title, v.Description, v.Industry, v.Location, v.ReqSkill, v.EXPRequired, e.ComName
                FROM VacancyJob v
                JOIN Employer e ON v.EmployerID = e.UserID
                WHERE v.Status = 'Open'
            """
            if industry:
                conditions.append("v.Industry = ?")
                values.append(industry)
            if location:
                conditions.append("v.Location = ?")
                values.append(location)
            if exp_input:
                conditions.append("v.EXPRequired <= ?")
                values.append(exp)
            if conditions:
                query += " AND " + " AND ".join(conditions)
            cursor.execute(query, *values)
            rows = cursor.fetchall()
            if rows:
                print("\nFiltered Vacancies:")
                for row in rows:
                    print(f"JobID: {row.JobID}, Title: {row.Title}, Description: {row.Description}, "
                          f"Industry: {row.Industry}, Location: {row.Location}, Skills: {row.ReqSkill}, "
                          f"Min Experience: {row.EXPRequired}, Company: {row.ComName}")
            else:
                print("No vacancies match the criteria.")
        except Exception as e:
            print(f"Error: Filter error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def filter_job_seekers():
    industry = input("Enter Industry (or press Enter to skip): ").strip() or None
    location = input("Enter Location (or press Enter to skip): ").strip() or None
    exp_input = input("Enter Minimum Experience (or press Enter to skip): ").strip() or None
    if exp_input:
        try:
            exp = int(exp_input)
            if exp < 0:
                print("Error: Experience cannot be negative!")
                return
        except ValueError:
            print("Error: Minimum experience must be a valid number!")
            return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            conditions = []
            values = []
            query = """
                SELECT u.UserID, u.Name, u.Email, j.Industry, j.PreferredLocation
                FROM [User] u
                JOIN JobSeeker j ON u.UserID = j.UserID
                WHERE u.Role = 1
            """
            if exp_input:
                query = """
                    SELECT DISTINCT u.UserID, u.Name, u.Email, j.Industry, j.PreferredLocation
                    FROM [User] u
                    JOIN JobSeeker j ON u.UserID = j.UserID
                    JOIN HasSkills hs ON j.UserID = hs.UserID
                    WHERE u.Role = 1 AND hs.EXPYears >= ?
                """
                values.append(exp)
            if industry:
                conditions.append("j.Industry = ?")
                values.append(industry)
            if location:
                conditions.append("j.PreferredLocation = ?")
                values.append(location)
            if conditions:
                query += " AND " + " AND ".join(conditions)
            cursor.execute(query, *values)
            rows = cursor.fetchall()
            if rows:
                print("\nFiltered Job Seekers:")
                for row in rows:
                    print(f"UserID: {row.UserID}, Name: {row.Name}, Email: {row.Email}, "
                          f"Industry: {row.Industry}, Preferred Location: {row.PreferredLocation}")
            else:
                print("No job seekers match the criteria.")
        except Exception as e:
            print(f"Error: Filter error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def show_job_details():
    job_id_input = input("Enter Job ID: ").strip()
    if not job_id_input:
        print("Error: Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        print("Error: Job ID must be a valid number!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT v.Title, v.Description, v.Industry, v.Location, v.ReqSkill, v.EXPRequired, e.ComName
                FROM VacancyJob v
                JOIN Employer e ON v.EmployerID = e.UserID
                WHERE v.JobID = ?
            """, job_id)
            job = cursor.fetchone()
            if job:
                print(f"\nJob Details (ID: {job_id}):")
                print(f"Title: {job.Title}")
                print(f"Description: {job.Description}")
                print(f"Industry: {job.Industry}")
                print(f"Location: {job.Location}")
                print(f"Required Skills: {job.ReqSkill}")
                print(f"Min Experience: {job.EXPRequired}")
                print(f"Company: {job.ComName}")
            else:
                print(f"No job found with JobID: {job_id}")
        except Exception as e:
            print(f"Error: Error fetching job details: {str(e)}")
        finally:
            cursor.close()
            conn.close()

# ─── User Management Functions ──────────────────────────────────────────
def update_user():
    if not logged_in_user:
        print("Error: You must be logged in to update your details!")
        return
    name = input("Enter New Name (or press Enter to skip): ").strip() or None
    email = input("Enter New Email (or press Enter to skip): ").strip() or None
    phone = input("Enter New Phone (or press Enter to skip): ").strip() or None
    password = input("Enter New Password (or press Enter to skip): ").strip() or None

    if email and ("@" not in email or "." not in email):
        print("Error: Invalid email format! Must contain '@' and '.'")
        return
    if phone and not phone.isdigit():
        print("Error: Phone must be digits only!")
        return
    if password and len(password) < 6:
        print("Error: Password must be at least 6 characters!")
        return
    if not any([name, email, phone, password]):
        print("Error: No update fields provided!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            updates = []
            values = []
            if name:
                updates.append("Name = ?")
                values.append(name)
            if email:
                updates.append("Email = ?")
                values.append(email)
            if phone:
                updates.append("Phone = ?")
                values.append(phone)
            if password:
                updates.append("Password = ?")
                values.append(password)
            set_clause = ", ".join(updates)
            values.append(logged_in_user['user_id'])
            cursor.execute(f"UPDATE [User] SET {set_clause} WHERE UserID = ?", *values)
            conn.commit()
            print("User updated successfully!")
        except pyodbc.IntegrityError:
            print("Error: Email already exists!")
        except Exception as e:
            conn.rollback()
            print(f"Error: Update error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def delete_user():
    if not logged_in_user:
        print("Error: You must be logged in to delete your account!")
        return
    email = input("Enter your Email to confirm deletion: ").strip()
    if logged_in_user['email'] != email:
        print("Error: You can only delete your own account!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT UserID, Role FROM [User] WHERE Email = ?", email)
            user = cursor.fetchone()
            if not user:
                print(f"Error: No user found with email: {email}")
                return
            user_id = user.UserID
            role = user.Role
            if role == 0:
                cursor.execute("DELETE FROM Application WHERE JobID IN (SELECT JobID FROM VacancyJob WHERE EmployerID = ?)", user_id)
                cursor.execute("DELETE FROM SavedVacancy WHERE JobID IN (SELECT JobID FROM VacancyJob WHERE EmployerID = ?)", user_id)
                cursor.execute("DELETE FROM VacancyJob WHERE EmployerID = ?", user_id)
                cursor.execute("DELETE FROM Employer WHERE UserID = ?", user_id)
            else:
                cursor.execute("DELETE FROM Application WHERE SeekerID = ?", user_id)
                cursor.execute("DELETE FROM SavedVacancy WHERE SeekerID = ?", user_id)
                cursor.execute("DELETE FROM HasSkills WHERE UserID = ?", user_id)
                cursor.execute("DELETE FROM JobSeeker WHERE UserID = ?", user_id)
            cursor.execute("DELETE FROM [User] WHERE Email = ?", email)
            conn.commit()
            print("User deleted successfully!")
            logout()
        except Exception as e:
            conn.rollback()
            print(f"Error: Delete error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

# ─── Analytics Functions ──────────────────────────────────────────
def most_interesting_job():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT v.Title, v.AppCount
                FROM VacancyJob v
                WHERE v.AppCount = (SELECT MAX(AppCount) FROM VacancyJob)
            """)
            row = cursor.fetchone()
            if row:
                print(f"Most Interesting Job: {row.Title}, Applicants: {row.AppCount}")
            else:
                print("No jobs found.")
        except Exception as e:
            print(f"Error: Query error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def job_no_applicants_last_month():
    last_month_start = datetime.now().replace(day=1) - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1)
    last_month_end = last_month_start.replace(day=28) + timedelta(days=4)
    last_month_end = last_month_end.replace(day=1) - timedelta(days=1)

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT v.Title
                FROM VacancyJob v
                LEFT JOIN Application a ON v.JobID = a.JobID
                AND a.ApplyDate BETWEEN ? AND ?
                WHERE v.Status = 'Open' AND a.AppID IS NULL
            """, last_month_start.date(), last_month_end.date())
            rows = cursor.fetchall()
            if rows:
                print("\nJobs with No Applicants Last Month:")
                for row in rows:
                    print(row.Title)
            else:
                print("No jobs without applicants last month.")
        except Exception as e:
            print(f"Error: Query error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def employer_max_announcements():
    last_month_start = datetime.now().replace(day=1) - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1)
    last_month_end = last_month_start.replace(day=28) + timedelta(days=4)
    last_month_end = last_month_end.replace(day=1) - timedelta(days=1)

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT e.ComName, COUNT(DISTINCT a.JobID) as JobCount
                FROM Employer e
                LEFT JOIN VacancyJob v ON e.UserID = v.EmployerID
                LEFT JOIN Application a ON v.JobID = a.JobID
                AND a.ApplyDate BETWEEN ? AND ?
                GROUP BY e.ComName
                HAVING COUNT(DISTINCT a.JobID) = (
                    SELECT MAX(JobCount)
                    FROM (
                        SELECT COUNT(DISTINCT a2.JobID) as JobCount
                        FROM VacancyJob v2
                        JOIN Application a2 ON v2.JobID = a2.JobID
                        WHERE a2.ApplyDate BETWEEN ? AND ?
                        GROUP BY v2.EmployerID
                    ) AS sub
                )
            """, last_month_start.date(), last_month_end.date(),
                last_month_start.date(), last_month_end.date())
            row = cursor.fetchone()
            if row:
                print(f"Employer with Max Announcements: {row.ComName}, Jobs with Applications: {row.JobCount}")
            else:
                print("No jobs with applications last month.")
        except Exception as e:
            print(f"Error: Query error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def employers_no_announcements():
    last_month_start = datetime.now().replace(day=1) - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1)
    last_month_end = last_month_start.replace(day=28) + timedelta(days=4)
    last_month_end = last_month_end.replace(day=1) - timedelta(days=1)

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT e.ComName
                FROM Employer e
                LEFT JOIN VacancyJob v ON e.UserID = v.EmployerID
                LEFT JOIN Application a ON v.JobID = a.JobID
                AND a.ApplyDate BETWEEN ? AND ?
                WHERE a.AppID IS NULL OR v.JobID IS NULL
                GROUP BY e.ComName
            """, last_month_start.date(), last_month_end.date())
            rows = cursor.fetchall()
            if rows:
                print("\nEmployers with No Announcements Last Month:")
                for row in rows:
                    print(row.ComName)
            else:
                print("All employers had jobs with applications last month.")
        except Exception as e:
            print(f"Error: Query error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def available_positions_last_month():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT e.ComName, v.Title
                FROM VacancyJob v
                JOIN Employer e ON v.EmployerID = e.UserID
                WHERE v.Status = 'Open'
                ORDER BY e.ComName
            """)
            rows = cursor.fetchall()
            if rows:
                result = {}
                for row in rows:
                    if row.ComName not in result:
                        result[row.ComName] = []
                    result[row.ComName].append(row.Title)
                print("\nAvailable Positions:")
                for emp, titles in result.items():
                    print(f"{emp}: {', '.join(titles)}")
            else:
                print("No open positions found.")
        except Exception as e:
            print(f"Error: Query error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def job_seeker_applications():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT u.UserID, u.Name, u.Email, u.Phone, j.Industry, j.PreferredLocation, j.AppliedJobCount
                FROM [User] u
                JOIN JobSeeker j ON u.UserID = j.UserID
                WHERE u.Role = 1
                ORDER BY u.Name
            """)
            rows = cursor.fetchall()
            if rows:
                print("\nJob Seeker Applications:")
                for row in rows:
                    print(f"Name: {row.Name}")
                    print(f"Email: {row.Email}")
                    print(f"Phone: {row.Phone}")
                    print(f"Industry: {row.Industry}")
                    print(f"Location: {row.PreferredLocation}")
                    print(f"Jobs Applied: {row.AppliedJobCount}\n")
            else:
                print("No job seekers found.")
        except Exception as e:
            print(f"Error: Query error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

# ─── Menu Functions ──────────────────────────────────────────
def employer_menu():
    while True:
        print("\nEmployer Menu:")
        print("1. Create Job")
        print("2. Hide Job")
        print("3. Delete Job")
        print("4. List Jobs")
        print("5. List Applications")
        print("6. Accept Application")
        print("7. Reject Application")
        print("8. Update User")
        print("9. Delete User")
        print("10. Filter Job Seekers")
        print("11. Analytics")
        print("12. Logout")
        choice = input("Enter choice (1-12): ").strip()

        if choice == "1":
            create_job()
        elif choice == "2":
            hide_job()
        elif choice == "3":
            delete_job()
        elif choice == "4":
            list_jobs()
        elif choice == "5":
            list_applications()
        elif choice == "6":
            accept_application()
        elif choice == "7":
            reject_application()
        elif choice == "8":
            update_user()
        elif choice == "9":
            delete_user()
            if not logged_in_user:
                break
        elif choice == "10":
            filter_job_seekers()
        elif choice == "11":
            analytics_menu()
        elif choice == "12":
            logout()
            break
        else:
            print("Invalid choice! Please try again.")

def job_seeker_menu():
    while True:
        print("\nJobSeeker Menu:")
        print("1. Apply for Job")
        print("2. Save Job")
        print("3. List Jobs")
        print("4. List Saved Jobs")
        print("5. Filter Vacancies")
        print("6. Show Job Details")
        print("7. Update User")
        print("8. Delete User")
        print("9. Analytics")
        print("10. Logout")
        choice = input("Enter choice (1-10): ").strip()

        if choice == "1":
            apply_for_job()
        elif choice == "2":
            save_job()
        elif choice == "3":
            list_jobs()
        elif choice == "4":
            list_saved_jobs()
        elif choice == "5":
            filter_vacancies()
        elif choice == "6":
            show_job_details()
        elif choice == "7":
            update_user()
        elif choice == "8":
            delete_user()
            if not logged_in_user:
                break
        elif choice == "9":
            analytics_menu()
        elif choice == "10":
            logout()
            break
        else:
            print("Invalid choice! Please try again.")

def analytics_menu():
    while True:
        print("\nAnalytics Menu:")
        print("1. Most Interesting Job")
        print("2. Jobs with No Applicants Last Month")
        print("3. Employer with Max Announcements")
        print("4. Employers with No Announcements")
        print("5. Available Positions")
        print("6. Job Seeker Applications")
        print("7. Back")
        choice = input("Enter choice (1-7): ").strip()

        if choice == "1":
            most_interesting_job()
        elif choice == "2":
            job_no_applicants_last_month()
        elif choice == "3":
            employer_max_announcements()
        elif choice == "4":
            employers_no_announcements()
        elif choice == "5":
            available_positions_last_month()
        elif choice == "6":
            job_seeker_applications()
        elif choice == "7":
            break
        else:
            print("Invalid choice! Please try again.")

def main_menu():
    while True:
        print("\nMain Menu:")
        print("1. Login")
        print("2. Register")
        print("3. Exit")
        choice = input("Enter choice (1-3): ").strip()

        if choice == "1":
            if login():
                if logged_in_user['role'] == 'Employer':
                    employer_menu()
                else:
                    job_seeker_menu()
        elif choice == "2":
            register_user()
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice! Please try again.")

if __name__ == "__main__":
    main_menu()