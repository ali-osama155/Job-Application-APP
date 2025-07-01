import tkinter as tk
from tkinter import ttk, messagebox
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

# Color schemes for light and dark modes
LIGHT_COLORS = {
    "BG_COLOR": "#F5F7FA",
    "FRAME_COLOR": "#E0E6F0",
    "BUTTON_COLOR": "#4681F4",
    "TEXT_COLOR": "#333333",
    "LABEL_COLOR": "#333333"
}

DARK_COLORS = {
    "BG_COLOR": "#435a62",
    "FRAME_COLOR": "#46506A",
    "BUTTON_COLOR": "#4c3081",
    "TEXT_COLOR": "#FFFFFF",
    "LABEL_COLOR": "#C0C0C0"
}

# Global variables
current_colors = LIGHT_COLORS.copy()
is_dark_mode = False
logged_in_user = None

def get_connection():
    """Establish database connection with error handling"""
    try:
        conn = pyodbc.connect(CONN_STR)
        return conn
    except Exception as e:
        messagebox.showerror("Connection Error",
                             f"Failed to connect to database: {str(e)}")
        return None

# ─── Theme Management ───────────────────────────────────────────
def toggle_theme():
    global current_colors, is_dark_mode
    is_dark_mode = not is_dark_mode
    current_colors = DARK_COLORS.copy() if is_dark_mode else LIGHT_COLORS.copy()
    apply_theme()

def apply_theme():
    root.configure(bg=current_colors["BG_COLOR"])
    for widget in root.winfo_children():
        update_widget_colors(widget)
    for tab in notebook.winfo_children():
        update_widget_colors(tab)

def update_widget_colors(widget):
    if isinstance(widget, tk.Frame) or isinstance(widget, ttk.Frame):
        widget.configure(bg=current_colors["FRAME_COLOR"])
    if isinstance(widget, tk.Label):
        widget.configure(
            bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"])
    if isinstance(widget, tk.Button):
        widget.configure(bg=current_colors["BUTTON_COLOR"], fg="white")
    if isinstance(widget, ttk.Treeview):
        style = ttk.Style()
        style.configure("Treeview", background=current_colors["FRAME_COLOR"],
                        fieldbackground=current_colors["FRAME_COLOR"], foreground=current_colors["TEXT_COLOR"])
    for child in widget.winfo_children():
        update_widget_colors(child)

# ─── Authentication Functions ───────────────────────────────────────────
def login():
    global logged_in_user
    email = login_email_entry.get().strip()
    password = login_password_entry.get().strip()

    if not email or "@" not in email or "." not in email:
        messagebox.showerror(
            "Login Error", "Invalid email format! Must contain '@' and '.'")
        return
    if len(password) < 6:
        messagebox.showerror(
            "Login Error", "Password must be at least 6 characters!")
        return

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
                messagebox.showinfo(
                    "Success", f"Login successful! Welcome {user_info['name']}")

                notebook.tab(0, state="hidden")
                notebook.tab(1, state="hidden")
                notebook.tab(
                    2, state="normal" if user_info['role'] == 'Employer' else "disabled")
                notebook.tab(
                    3, state="normal" if user_info['role'] == 'JobSeeker' else "disabled")
                notebook.tab(4, state="normal")
                notebook.tab(5, state="normal")
                notebook.select(2 if user_info['role'] == 'Employer' else 3)

                update_job_tree()
                update_user_tree()
                update_saved_jobs_tree()
                update_applications_tree()
                logout_button.pack(side=tk.RIGHT, padx=10)
            else:
                messagebox.showerror(
                    "Login Error", "Invalid email or password")
        except Exception as e:
            messagebox.showerror("Login Error", f"Login failed: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def register_user():
    name = reg_name_entry.get().strip()
    email = reg_email_entry.get().strip()
    phone = reg_phone_entry.get().strip()
    role = 0 if role_var.get() == "Employer" else 1
    password = reg_password_entry.get().strip()

    if not name:
        messagebox.showerror("Error", "Name cannot be empty!")
        return
    if not email or "@" not in email or "." not in email:
        messagebox.showerror(
            "Error", "Invalid email format! Must contain '@' and '.'")
        return
    if not phone.isdigit():
        messagebox.showerror("Error", "Phone must be digits only!")
        return
    if len(password) < 6:
        messagebox.showerror(
            "Error", "Password must be at least 6 characters!")
        return

    if role == 0:
        company_name = reg_company_entry.get().strip()
        industry = reg_industry_entry.get().strip()
        location = reg_location_entry.get().strip()
        if not all([company_name, industry, location]):
            messagebox.showerror("Error", "All Employer fields are required!")
            return
        kwargs = {"company_name": company_name,
                  "industry": industry, "location": location}
    else:
        resume_link = reg_resume_entry.get().strip()
        industry = reg_js_industry_entry.get().strip()
        location = reg_js_location_entry.get().strip()
        if not all([resume_link, industry, location]):
            messagebox.showerror("Error", "All JobSeeker fields are required!")
            return
        kwargs = {"resume_link": resume_link,
                  "industry": industry, "location": location}

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO [User] (Name, Email, Phone, Role, Password)
                OUTPUT INSERTED.UserID
                VALUES (?, ?, ?, ?, ?)
            """, name, email, phone, role, password)
            user_id = cursor.fetchone().UserID

            if role == 0:
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
            messagebox.showinfo(
                "Success", f"User registered successfully! UserID: {user_id}")
            clear_fields()
            notebook.select(0)
            logged_in_user = None
        except pyodbc.IntegrityError:
            messagebox.showerror("Error", "Email already exists!")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to register user: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def clear_fields():
    reg_name_entry.delete(0, tk.END)
    reg_email_entry.delete(0, tk.END)
    reg_phone_entry.delete(0, tk.END)
    reg_password_entry.delete(0, tk.END)
    reg_company_entry.delete(0, tk.END)
    reg_industry_entry.delete(0, tk.END)
    reg_location_entry.delete(0, tk.END)
    reg_resume_entry.delete(0, tk.END)
    reg_js_industry_entry.delete(0, tk.END)
    reg_js_location_entry.delete(0, tk.END)

def logout():
    global logged_in_user
    logged_in_user = None
    notebook.tab(0, state="normal")
    notebook.tab(1, state="normal")
    notebook.tab(2, state="disabled")
    notebook.tab(3, state="disabled")
    notebook.tab(4, state="disabled")
    notebook.tab(5, state="disabled")
    notebook.select(0)
    logout_button.pack_forget()
    messagebox.showinfo("Success", "Logged out successfully!")

# ─── Job Management Functions ──────────────────────────────────────────
def create_job():
    title = title_entry_employer.get().strip()
    desc = desc_entry_employer.get().strip()
    industry = industry_entry_employer.get().strip()
    location = location_entry_employer.get().strip()
    skills = skills_entry_employer.get().strip()
    exp_input = exp_entry_employer.get().strip()
    if not exp_input:
        messagebox.showerror("Error", "Minimum experience is required!")
        return
    try:
        exp = int(exp_input)
        if exp < 0:
            messagebox.showerror("Error", "Experience cannot be negative!")
            return
    except ValueError:
        messagebox.showerror("Error", "Minimum experience must be a valid number!")
        return
    if not all([title, desc, industry, location, skills]):
        messagebox.showerror("Error", "All fields are required!")
        return
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        messagebox.showerror("Error", "You must be logged in as an Employer to create a job!")
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
            messagebox.showinfo("Success", f"Job created successfully! JobID: {job_id}")
            clear_job_fields()
            update_job_tree()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to create job: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def clear_job_fields():
    title_entry_employer.delete(0, tk.END)
    desc_entry_employer.delete(0, tk.END)
    industry_entry_employer.delete(0, tk.END)
    location_entry_employer.delete(0, tk.END)
    skills_entry_employer.delete(0, tk.END)
    exp_entry_employer.delete(0, tk.END)

def hide_job():
    job_id_input = job_id_entry_employer.get().strip()
    if not job_id_input:
        messagebox.showerror("Error", "Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        messagebox.showerror("Error", "Job ID must be a valid number!")
        return
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        messagebox.showerror("Error", "You must be logged in as an Employer to hide a job!")
        return
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT JobID FROM VacancyJob WHERE JobID = ? AND EmployerID = ?", job_id, logged_in_user['user_id'])
            job = cursor.fetchone()
            if not job:
                messagebox.showerror("Error", f"No job found with JobID: {job_id} for this Employer!")
                return
            cursor.execute("UPDATE VacancyJob SET Status = 'Closed' WHERE JobID = ?", job_id)
            conn.commit()
            messagebox.showinfo("Success", f"JobID: {job_id} has been hidden successfully")
            job_id_entry_employer.delete(0, tk.END)
            update_job_tree()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Hide error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def delete_user():
    email = reg_email_entry.get().strip()
    if not logged_in_user or logged_in_user['email'] != email:
        messagebox.showerror("Error", "You can only delete your own account!")
        return
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT UserID, Role FROM [User] WHERE Email = ?", email)
            user = cursor.fetchone()
            if not user:
                messagebox.showerror(
                    "Error", f"No user found with email: {email}")
                return
            user_id = user.UserID
            role = user.Role
            if role == 0:
                cursor.execute(
                    "DELETE FROM Application WHERE JobID IN (SELECT JobID FROM VacancyJob WHERE EmployerID = ?)", user_id)
                cursor.execute(
                    "DELETE FROM SavedVacancy WHERE JobID IN (SELECT JobID FROM VacancyJob WHERE EmployerID = ?)", user_id)
                cursor.execute(
                    "DELETE FROM VacancyJob WHERE EmployerID = ?", user_id)
                cursor.execute(
                    "DELETE FROM Employer WHERE UserID = ?", user_id)
            else:
                cursor.execute(
                    "DELETE FROM Application WHERE SeekerID = ?", user_id)
                cursor.execute(
                    "DELETE FROM SavedVacancy WHERE SeekerID = ?", user_id)
                cursor.execute(
                    "DELETE FROM HasSkills WHERE UserID = ?", user_id)
                cursor.execute(
                    "DELETE FROM JobSeeker WHERE UserID = ?", user_id)
            cursor.execute("DELETE FROM [User] WHERE Email = ?", email)
            conn.commit()
            logout()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Delete error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def delete_job():
    job_id_input = job_id_entry_employer.get().strip()
    if not job_id_input:
        messagebox.showerror("Error", "Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        messagebox.showerror("Error", "Job ID must be a valid number!")
        return
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        messagebox.showerror("Error", "You must be logged in as an Employer to delete a job!")
        return
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT EmployerID FROM VacancyJob WHERE JobID = ?", job_id)
            job = cursor.fetchone()
            if not job:
                messagebox.showerror("Error", f"No job found with JobID: {job_id}")
                return
            if job.EmployerID != logged_in_user['user_id']:
                messagebox.showerror("Error", "You can only delete jobs that you created!")
                return
            cursor.execute("DELETE FROM Application WHERE JobID = ?", job_id)
            cursor.execute("DELETE FROM SavedVacancy WHERE JobID = ?", job_id)
            cursor.execute("DELETE FROM VacancyJob WHERE JobID = ?", job_id)
            cursor.execute("UPDATE Employer SET AnnouncedJobCount = AnnouncedJobCount - 1 WHERE UserID = ?",
                           logged_in_user['user_id'])
            conn.commit()
            messagebox.showinfo("Success", f"Deleted job with JobID: {job_id}")
            job_id_entry_employer.delete(0, tk.END)
            update_job_tree()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Delete error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def update_user():
    name = name_entry.get().strip() or None
    email = email_entry.get().strip() or None
    phone = phone_entry.get().strip() or None
    password = password_entry.get().strip() or None

    if email and ("@" not in email or "." not in email):
        messagebox.showerror(
            "Error", "Invalid email format! Must contain '@' and '.'")
        return
    if phone and not phone.isdigit():
        messagebox.showerror("Error", "Phone must be digits only!")
        return
    if password and len(password) < 6:
        messagebox.showerror(
            "Error", "Password must be at least 6 characters!")
        return
    if not any([name, email, phone, password]):
        messagebox.showerror("Error", "No update fields provided!")
        return
    if not logged_in_user:
        messagebox.showerror(
            "Error", "You must be logged in to update your details!")
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
            cursor.execute(
                f"UPDATE [User] SET {set_clause} WHERE UserID = ?", *values)
            conn.commit()
            messagebox.showinfo("Success", "User updated successfully!")
            clear_fields()
            update_user_tree()
        except pyodbc.IntegrityError:
            messagebox.showerror("Error", "Email already exists!")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Update error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def update_job():
    job_id_input = job_id_entry_employer.get().strip()
    if not job_id_input:
        messagebox.showerror("Error", "Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        messagebox.showerror("Error", "Job ID must be a valid number!")
        return

    title = title_entry_employer.get().strip() or None
    desc = desc_entry_employer.get().strip() or None
    industry = industry_entry_employer.get().strip() or None
    location = location_entry_employer.get().strip() or None
    skills = skills_entry_employer.get().strip() or None
    exp_input = exp_entry_employer.get().strip() or None

    if exp_input:
        try:
            exp = int(exp_input)
            if exp < 0:
                messagebox.showerror("Error", "Experience cannot be negative!")
                return
        except ValueError:
            messagebox.showerror("Error", "Minimum experience must be a valid number!")
            return
    else:
        exp = None

    if not any([title, desc, industry, location, skills, exp is not None]):
        messagebox.showerror("Error", "No update fields provided!")
        return
    if not logged_in_user or logged_in_user['role'] != 'Employer':
        messagebox.showerror("Error", "You must be logged in as an Employer to update job details!")
        return

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            updates = []
            values = []
            if title:
                updates.append("Title = ?")
                values.append(title)
            if desc:
                updates.append("Description = ?")
                values.append(desc)
            if industry:
                updates.append("Industry = ?")
                values.append(industry)
            if location:
                updates.append("Location = ?")
                values.append(location)
            if skills:
                updates.append("ReqSkill = ?")
                values.append(skills)
            if exp is not None:
                updates.append("EXPRequired = ?")
                values.append(exp)
            set_clause = ", ".join(updates)
            values.append(job_id)
            cursor.execute(f"UPDATE VacancyJob SET {set_clause} WHERE JobID = ?", *values)
            conn.commit()
            messagebox.showinfo("Success", f"Job updated successfully! JobID: {job_id}")
            clear_job_fields()
            update_job_tree()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Update error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def update_user_tree():
    for item in user_tree.get_children():
        user_tree.delete(item)
    conn = get_connection()
    if conn and logged_in_user and logged_in_user['role'] == 'Employer':
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT UserID, Name, Email, Role FROM [User]")
            rows = cursor.fetchall()
            for row in rows:
                role = "Employer" if row.Role == 0 else "JobSeeker"
                user_tree.insert("", tk.END, values=(
                    row.UserID, row.Name, row.Email, role))
        except Exception as e:
            messagebox.showerror("Error", f"Select error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def update_job_tree():
    for item in job_tree.get_children():
        job_tree.delete(item)
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
            for row in rows:
                job_tree.insert("", tk.END, values=(
                    row.JobID, row.Title, row.Location, row.ComName, row.ComIndustry))
        except Exception as e:
            messagebox.showerror("Error", f"Select error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def update_saved_jobs_tree():
    for item in saved_jobs_tree.get_children():
        saved_jobs_tree.delete(item)
    if not logged_in_user or logged_in_user['role'] != 'JobSeeker':
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
            for row in rows:
                saved_jobs_tree.insert("", tk.END, values=(
                    row.JobID, row.Title, row.Description, row.Industry, row.Location))
        except Exception as e:
            messagebox.showerror("Error", f"Select error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def update_applications_tree():
    for item in applications_tree.get_children():
        applications_tree.delete(item)
    if not logged_in_user or logged_in_user['role'] != 'Employer':
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
            for row in rows:
                applications_tree.insert("", tk.END, values=(
                    row.AppID, row.JobID, row.Title, row.Name, row.Status))
        except Exception as e:
            messagebox.showerror("Error", f"Select error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def filter_vacancies():
    industry = industry_entry_filter.get().strip() or None
    location = location_entry_filter.get().strip() or None
    exp_input = exp_entry_filter.get().strip() or None
    if exp_input:
        try:
            exp = int(exp_input)
            if exp < 0:
                messagebox.showerror("Error", "Experience cannot be negative!")
                return
        except ValueError:
            messagebox.showerror("Error", "Maximum experience must be a valid number!")
            return

    for item in filtered_vacancies_tree.get_children():
        filtered_vacancies_tree.delete(item)
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
            for row in rows:
                filtered_vacancies_tree.insert("", tk.END, values=(
                    row.JobID, row.Title, row.Description, row.Industry, row.Location, row.ReqSkill, row.EXPRequired, row.ComName))
        except Exception as e:
            messagebox.showerror("Error", f"Filter error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def filter_job_seekers():
    industry = industry_entry_seeker.get().strip() or None
    location = location_entry_seeker.get().strip() or None
    exp_input = exp_entry_seeker.get().strip() or None
    if exp_input:
        try:
            exp = int(exp_input)
            if exp < 0:
                messagebox.showerror("Error", "Experience cannot be negative!")
                return
        except ValueError:
            messagebox.showerror(
                "Error", "Minimum experience must be a valid number!")
            return

    for item in filtered_seekers_tree.get_children():
        filtered_seekers_tree.delete(item)
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
            for row in rows:
                filtered_seekers_tree.insert("", tk.END, values=(
                    row.UserID, row.Name, row.Email, row.Industry, row.PreferredLocation))
        except Exception as e:
            messagebox.showerror("Error", f"Filter error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def apply_for_job():
    job_id_input = job_id_entry_seeker.get().strip()
    if not job_id_input:
        messagebox.showerror("Error", "Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        messagebox.showerror("Error", "Job ID must be a valid number!")
        return
    if not logged_in_user or logged_in_user['role'] != 'JobSeeker':
        messagebox.showerror(
            "Error", "You must be logged in as a JobSeeker to apply for a job!")
        return
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT Status FROM VacancyJob WHERE JobID = ?", job_id)
            job = cursor.fetchone()
            if not job:
                messagebox.showerror(
                    "Error", f"No job found with JobID: {job_id}")
                return
            if job.Status != 'Open':
                messagebox.showerror(
                    "Error", "This job is not open for applications!")
                return
            cursor.execute("SELECT AppID FROM Application WHERE SeekerID = ? AND JobID = ?",
                           logged_in_user['user_id'], job_id)
            if cursor.fetchone():
                messagebox.showerror(
                    "Error", "You have already applied for this job!")
                return
            cursor.execute("INSERT INTO Application (JobID, SeekerID, Status, ApplyDate) VALUES (?, ?, 'Pending', ?)",
                           job_id, logged_in_user['user_id'], datetime.now().date())
            cursor.execute(
                "UPDATE VacancyJob SET AppCount = AppCount + 1 WHERE JobID = ?", job_id)
            cursor.execute(
                "UPDATE JobSeeker SET AppliedJobCount = AppliedJobCount + 1 WHERE UserID = ?", logged_in_user['user_id'])
            conn.commit()
            messagebox.showinfo(
                "Success", f"Successfully applied for JobID: {job_id}")
            job_id_entry_seeker.delete(0, tk.END)
            update_applications_tree()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Apply error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def save_job():
    job_id_input = job_id_entry_seeker.get().strip()
    if not job_id_input:
        messagebox.showerror("Error", "Job ID is required!")
        return
    try:
        job_id = int(job_id_input)
    except ValueError:
        messagebox.showerror("Error", "Job ID must be a valid number!")
        return
    if not logged_in_user or logged_in_user['role'] != 'JobSeeker':
        messagebox.showerror(
            "Error", "You must be logged in as a JobSeeker to save a job!")
        return
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT Status FROM VacancyJob WHERE JobID = ?", job_id)
            job = cursor.fetchone()
            if not job:
                messagebox.showerror(
                    "Error", f"No job found with JobID: {job_id}")
                return
            if job.Status != 'Open':
                messagebox.showerror(
                    "Error", "This job is not open and cannot be saved!")
                return
            cursor.execute("SELECT JobID FROM SavedVacancy WHERE SeekerID = ? AND JobID = ?",
                           logged_in_user['user_id'], job_id)
            if cursor.fetchone():
                messagebox.showerror(
                    "Error", "You have already saved this job!")
                return
            cursor.execute("INSERT INTO SavedVacancy (JobID, SeekerID, SaveDate) VALUES (?, ?, ?)",
                           job_id, logged_in_user['user_id'], datetime.now().date())
            conn.commit()
            messagebox.showinfo(
                "Success", f"Successfully saved JobID: {job_id}")
            job_id_entry_seeker.delete(0, tk.END)
            update_saved_jobs_tree()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Save error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def show_job_details(event):
    selected_item = job_tree.selection()
    if not selected_item:
        return
    job_id_value = job_tree.item(selected_item)['values'][0]
    if not job_id_value or not str(job_id_value).isdigit():
        messagebox.showerror("Error", "Invalid Job ID selected!")
        return
    job_id = int(job_id_value)
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
                details = f"Title: {job.Title}\nDescription: {job.Description}\nIndustry: {job.Industry}\nLocation: {job.Location}\nRequired Skills: {job.ReqSkill}\nMin Experience: {job.EXPRequired}\nCompany: {job.ComName}"
                messagebox.showinfo(f"Job Details (ID: {job_id})", details)
        except Exception as e:
            messagebox.showerror(
                "Error", f"Error fetching job details: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def update_application_status(app_id, new_status):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE Application SET Status = ? WHERE AppID = ?", new_status, app_id)
            conn.commit()
            messagebox.showinfo(
                "Success", f"Application status updated to {new_status}")
            update_applications_tree()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Update error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

def accept_application():
    selected_item = applications_tree.selection()
    if not selected_item:
        messagebox.showerror("Error", "Please select an application!")
        return
    app_id = applications_tree.item(selected_item)['values'][0]
    update_application_status(app_id, "Accepted")

def reject_application():
    selected_item = applications_tree.selection()
    if not selected_item:
        messagebox.showerror("Error", "Please select an application!")
        return
    app_id = applications_tree.item(selected_item)['values'][0]
    update_application_status(app_id, "Rejected")

def toggle_fields():
    if role_var.get() == "Employer":
        company_frame.grid()
        seeker_frame.grid_remove()
    else:
        company_frame.grid_remove()
        seeker_frame.grid()

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
                messagebox.showinfo("Most Interesting Job",
                                    f"Job Title: {row.Title}\nApplicants: {row.AppCount}")
            else:
                messagebox.showinfo("Most Interesting Job", "No jobs found.")
        except Exception as e:
            messagebox.showerror("Error", f"Query error: {str(e)}")
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
                titles = "\n".join(row.Title for row in rows)
                messagebox.showinfo("Jobs with No Applicants Last Month",
                                    f"Job Titles:\n{titles}")
            else:
                messagebox.showinfo("Jobs with No Applicants Last Month",
                                    "No jobs without applicants last month.")
        except Exception as e:
            messagebox.showerror("Error", f"Query error: {str(e)}")
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
                messagebox.showinfo("Employer with Max Announcements",
                                    f"Employer: {row.ComName}\nJobs with Applications: {row.JobCount}")
            else:
                messagebox.showinfo("Employer with Max Announcements",
                                    "No jobs with applications last month.")
        except Exception as e:
            messagebox.showerror("Error", f"Query error: {str(e)}")
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
                employers = "\n".join(row.ComName for row in rows)
                messagebox.showinfo("Employers with No Announcements Last Month",
                                    f"Employers:\n{employers}")
            else:
                messagebox.showinfo("Employers with No Announcements Last Month",
                                    "All employers had jobs with applications last month.")
        except Exception as e:
            messagebox.showerror("Error", f"Query error: {str(e)}")
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
                output = "\n".join(
                    f"{emp}: {', '.join(titles)}" for emp, titles in result.items())
                messagebox.showinfo("Available Positions", output)
            else:
                messagebox.showinfo("Available Positions",
                                    "No open positions found.")
        except Exception as e:
            messagebox.showerror("Error", f"Query error: {str(e)}")
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
                output = "\n".join(
                    f"Name: {row.Name}\nEmail: {row.Email}\nPhone: {row.Phone}\nIndustry: {row.Industry}\nLocation: {row.PreferredLocation}\nJobs Applied: {row.AppliedJobCount}\n"
                    for row in rows)
                messagebox.showinfo("Job Seeker Applications", output)
            else:
                messagebox.showinfo("Job Seeker Applications",
                                    "No job seekers found.")
        except Exception as e:
            messagebox.showerror("Error", f"Query error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

# Initialize GUI
root = tk.Tk()
root.title("Job Application System")
root.geometry("1000x700")
root.configure(bg=current_colors["BG_COLOR"])

# Theme and logout buttons
theme_frame = tk.Frame(root, bg=current_colors["BG_COLOR"])
theme_frame.pack(fill=tk.X, pady=5)
tk.Button(theme_frame, text=" Dark Mode", command=toggle_theme,
          bg=current_colors["BUTTON_COLOR"], fg="white").pack(side=tk.RIGHT, padx=10)
logout_button = tk.Button(theme_frame, text="Logout", command=logout,
                          bg=current_colors["BUTTON_COLOR"], fg="white")

# Notebook for tabs
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True)

# Tab 0: Login
login_tab = tk.Frame(notebook, bg=current_colors["FRAME_COLOR"])
notebook.add(login_tab, text="Login")

tk.Label(login_tab, text="Login", font=("Arial", 16, "bold"),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["TEXT_COLOR"]).pack(pady=20)

login_frame = tk.Frame(login_tab, bg=current_colors["FRAME_COLOR"])
login_frame.pack(padx=20, pady=10)

tk.Label(login_frame, text="Email:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=0, column=0, padx=5, pady=5, sticky="e")
login_email_entry = tk.Entry(login_frame)
login_email_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(login_frame, text="Password:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
login_password_entry = tk.Entry(login_frame, show="*")
login_password_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Button(login_frame, text="Login", command=login,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=15).grid(row=2, column=0, columnspan=2, pady=10)
tk.Button(login_frame, text="Register", command=lambda: notebook.select(
    1), bg=current_colors["BUTTON_COLOR"], fg="white", width=15).grid(row=3, column=0, columnspan=2, pady=5)

# Tab 1: Register
register_tab = tk.Frame(notebook, bg=current_colors["FRAME_COLOR"])
notebook.add(register_tab, text="Register")

tk.Label(register_tab, text="Register New User", font=("Arial", 16, "bold"),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["TEXT_COLOR"]).pack(pady=20)

register_frame = tk.Frame(register_tab, bg=current_colors["FRAME_COLOR"])
register_frame.pack(padx=20, pady=10)

tk.Label(register_frame, text="Name:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=0, column=0, padx=5, pady=5, sticky="e")
reg_name_entry = tk.Entry(register_frame)
reg_name_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(register_frame, text="Email:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
reg_email_entry = tk.Entry(register_frame)
reg_email_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(register_frame, text="Phone:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=2, column=0, padx=5, pady=5, sticky="e")
reg_phone_entry = tk.Entry(register_frame)
reg_phone_entry.grid(row=2, column=1, padx=5, pady=5)

tk.Label(register_frame, text="Role:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=3, column=0, padx=5, pady=5, sticky="e")
role_var = tk.StringVar(value="Employer")
tk.Radiobutton(register_frame, text="Employer", variable=role_var, value="Employer",
               bg=current_colors["FRAME_COLOR"], command=toggle_fields).grid(row=3, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(register_frame, text="JobSeeker", variable=role_var, value="JobSeeker",
               bg=current_colors["FRAME_COLOR"], command=toggle_fields).grid(row=3, column=2, padx=5, pady=5, sticky="w")

tk.Label(register_frame, text="Password:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=4, column=0, padx=5, pady=5, sticky="e")
reg_password_entry = tk.Entry(register_frame, show="*")
reg_password_entry.grid(row=4, column=1, padx=5, pady=5)

company_frame = tk.Frame(register_frame, bg=current_colors["FRAME_COLOR"])
company_frame.grid(row=5, column=0, columnspan=3, pady=5)
tk.Label(company_frame, text="Company Name:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=0, column=0, padx=5, pady=5, sticky="e")
reg_company_entry = tk.Entry(company_frame)
reg_company_entry.grid(row=0, column=1, padx=5, pady=5)
tk.Label(company_frame, text="Industry:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
reg_industry_entry = tk.Entry(company_frame)
reg_industry_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Label(company_frame, text="Location:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=2, column=0, padx=5, pady=5, sticky="e")
reg_location_entry = tk.Entry(company_frame)
reg_location_entry.grid(row=2, column=1, padx=5, pady=5)

seeker_frame = tk.Frame(register_frame, bg=current_colors["FRAME_COLOR"])
seeker_frame.grid(row=6, column=0, columnspan=3, pady=5)
tk.Label(seeker_frame, text="Resume Link:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=0, column=0, padx=5, pady=5, sticky="e")
reg_resume_entry = tk.Entry(seeker_frame)
reg_resume_entry.grid(row=0, column=1, padx=5, pady=5)
tk.Label(seeker_frame, text="Preferred Industry:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
reg_js_industry_entry = tk.Entry(seeker_frame)
reg_js_industry_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Label(seeker_frame, text="Preferred Location:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=2, column=0, padx=5, pady=5, sticky="e")
reg_js_location_entry = tk.Entry(seeker_frame)
reg_js_location_entry.grid(row=2, column=1, padx=5, pady=5)

tk.Button(register_frame, text="Register", command=register_user,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=15).grid(row=7, column=0, columnspan=2, pady=5)
tk.Button(register_frame, text="Clear", command=clear_fields, bg="#0e3f4f",
          fg="white", width=15).grid(row=8, column=0, columnspan=2, pady=5)

# Tab 2: Employer Functions
employer_frame = tk.Frame(notebook, bg=current_colors["FRAME_COLOR"])
notebook.add(employer_frame, text="Employer Functions")

tk.Label(employer_frame, text="Employer Functions", font=("Arial", 16, "bold"),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["TEXT_COLOR"]).pack(pady=10)

job_frame = tk.Frame(employer_frame, bg=current_colors["FRAME_COLOR"])
job_frame.pack(padx=20, pady=10)

tk.Label(job_frame, text="Create Job:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(row=0, column=0, columnspan=2, pady=5)
tk.Label(job_frame, text="Job Title:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
title_entry_employer = tk.Entry(job_frame)
title_entry_employer.grid(row=1, column=1, padx=5, pady=5)

tk.Label(job_frame, text="Description:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=2, column=0, padx=5, pady=5, sticky="e")
desc_entry_employer = tk.Entry(job_frame)
desc_entry_employer.grid(row=2, column=1, padx=5, pady=5)

tk.Label(job_frame, text="Industry:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=3, column=0, padx=5, pady=5, sticky="e")
industry_entry_employer = tk.Entry(job_frame)
industry_entry_employer.grid(row=3, column=1, padx=5, pady=5)

tk.Label(job_frame, text="Location:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=4, column=0, padx=5, pady=5, sticky="e")
location_entry_employer = tk.Entry(job_frame)
location_entry_employer.grid(row=4, column=1, padx=5, pady=5)

tk.Label(job_frame, text="Required Skills:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=5, column=0, padx=5, pady=5, sticky="e")
skills_entry_employer = tk.Entry(job_frame)
skills_entry_employer.grid(row=5, column=1, padx=5, pady=5)

tk.Label(job_frame, text="Min Experience:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=6, column=0, padx=5, pady=5, sticky="e")
exp_entry_employer = tk.Entry(job_frame)
exp_entry_employer.grid(row=6, column=1, padx=5, pady=5)

tk.Label(job_frame, text="Job ID:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=10, column=0, padx=5, pady=5, sticky="e")
job_id_entry_employer = tk.Entry(job_frame)
job_id_entry_employer.grid(row=10, column=1, padx=5, pady=5)

tk.Button(job_frame, text="Create Job", command=create_job,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=7, column=0, columnspan=2, pady=5)
tk.Button(job_frame, text="Clear", command=clear_job_fields,
          bg="#0e3f4f", fg="white").grid(row=8, column=0, columnspan=2, pady=5)

tk.Label(job_frame, text="Hide/Delete Job:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(row=9, column=0, columnspan=2, pady=5)
tk.Label(job_frame, text="Job ID:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=10, column=0, padx=5, pady=5, sticky="e")
job_id_entry_employer = tk.Entry(job_frame)
job_id_entry_employer.grid(row=10, column=1, padx=5, pady=5)
tk.Button(job_frame, text="Hide Job", command=hide_job,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=11, column=0, pady=5)
tk.Button(job_frame, text="Delete Job", command=delete_job,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=11, column=1, pady=5)

job_tree_frame = tk.Frame(employer_frame, bg=current_colors["FRAME_COLOR"])
job_tree_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
job_tree = ttk.Treeview(job_tree_frame, columns=(
    "JobID", "Title", "Location", "Company", "Industry"), show="headings")
job_tree.heading("JobID", text="Job ID")
job_tree.heading("Title", text="Title")
job_tree.heading("Location", text="Location")
job_tree.heading("Company", text="Company")
job_tree.heading("Industry", text="Industry")
job_tree.pack(fill=tk.BOTH, expand=True)
job_tree.bind("<Double-1>", show_job_details)
update_job_tree()

applications_frame = tk.Frame(employer_frame, bg=current_colors["FRAME_COLOR"])
applications_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
tk.Label(applications_frame, text="Applications:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).pack(pady=5)
applications_tree = ttk.Treeview(applications_frame, columns=(
    "AppID", "JobID", "JobTitle", "SeekerName", "Status"), show="headings")
applications_tree.heading("AppID", text="App ID")
applications_tree.heading("JobID", text="Job ID")
applications_tree.heading("JobTitle", text="Job Title")
applications_tree.heading("SeekerName", text="Seeker Name")
applications_tree.heading("Status", text="Status")
applications_tree.pack(fill=tk.BOTH, expand=True)
btn_frame = tk.Frame(applications_frame, bg=current_colors["FRAME_COLOR"])
btn_frame.pack(pady=5)
tk.Button(btn_frame, text="Accept", command=accept_application,
          bg=current_colors["BUTTON_COLOR"], fg="white").pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Reject", command=reject_application,
          bg=current_colors["BUTTON_COLOR"], fg="white").pack(side=tk.LEFT, padx=5)
update_applications_tree()

# Tab 3: JobSeeker Functions
seeker_frame = tk.Frame(notebook, bg=current_colors["FRAME_COLOR"])
notebook.add(seeker_frame, text="JobSeeker Functions")

tk.Label(seeker_frame, text="JobSeeker Functions", font=("Arial", 16, "bold"),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["TEXT_COLOR"]).pack(pady=10)

apply_frame = tk.Frame(seeker_frame, bg=current_colors["FRAME_COLOR"])
apply_frame.pack(padx=20, pady=10)

tk.Label(apply_frame, text="Apply/Save Job:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(row=0, column=0, columnspan=2, pady=5)
tk.Label(apply_frame, text="Job ID:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
job_id_entry_seeker = tk.Entry(apply_frame)
job_id_entry_seeker.grid(row=1, column=1, padx=5, pady=5)
tk.Button(apply_frame, text="Apply for Job", command=apply_for_job,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=2, column=0, pady=5)
tk.Button(apply_frame, text="Save Job", command=save_job,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=2, column=1, pady=5)

filter_frame = tk.Frame(seeker_frame, bg=current_colors["FRAME_COLOR"])
filter_frame.pack(padx=20, pady=10)

tk.Label(filter_frame, text="Filter Vacancies:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(row=0, column=0, columnspan=2, pady=5)
tk.Label(filter_frame, text="Industry:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
industry_entry_filter = tk.Entry(filter_frame)
industry_entry_filter.grid(row=1, column=1, padx=5, pady=5)
tk.Label(filter_frame, text="Location:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=2, column=0, padx=5, pady=5, sticky="e")
location_entry_filter = tk.Entry(filter_frame)
location_entry_filter.grid(row=2, column=1, padx=5, pady=5)
tk.Label(filter_frame, text="Max Experience:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=3, column=0, padx=5, pady=5, sticky="e")
exp_entry_filter = tk.Entry(filter_frame)
exp_entry_filter.grid(row=3, column=1, padx=5, pady=5)
tk.Button(filter_frame, text="Filter Vacancies", command=filter_vacancies,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=4, column=0, columnspan=2, pady=5)

tk.Label(filter_frame, text="Filter Job Seekers:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(row=5, column=0, columnspan=2, pady=5)
tk.Label(filter_frame, text="Industry:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=6, column=0, padx=5, pady=5, sticky="e")
industry_entry_seeker = tk.Entry(filter_frame)
industry_entry_seeker.grid(row=6, column=1, padx=5, pady=5)
tk.Label(filter_frame, text="Location:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=7, column=0, padx=5, pady=5, sticky="e")
location_entry_seeker = tk.Entry(filter_frame)
location_entry_seeker.grid(row=7, column=1, padx=5, pady=5)
tk.Label(filter_frame, text="Min Experience:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=8, column=0, padx=5, pady=5, sticky="e")
exp_entry_seeker = tk.Entry(filter_frame)
exp_entry_seeker.grid(row=8, column=1, padx=5, pady=5)
tk.Button(filter_frame, text="Filter Seekers", command=filter_job_seekers,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=9, column=0, columnspan=2, pady=5)

filtered_vacancies_tree_frame = tk.Frame(
    seeker_frame, bg=current_colors["FRAME_COLOR"])
filtered_vacancies_tree_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
filtered_vacancies_tree = ttk.Treeview(filtered_vacancies_tree_frame, columns=(
    "JobID", "Title", "Description", "Industry", "Location", "Skills", "Experience", "Company"), show="headings")
filtered_vacancies_tree.heading("JobID", text="Job ID")
filtered_vacancies_tree.heading("Title", text="Title")
filtered_vacancies_tree.heading("Description", text="Description")
filtered_vacancies_tree.heading("Industry", text="Industry")
filtered_vacancies_tree.heading("Location", text="Location")
filtered_vacancies_tree.heading("Skills", text="Required Skills")
filtered_vacancies_tree.heading("Experience", text="Min Experience")
filtered_vacancies_tree.heading("Company", text="Company")
filtered_vacancies_tree.pack(fill=tk.BOTH, expand=True)

filtered_seekers_tree_frame = tk.Frame(
    seeker_frame, bg=current_colors["FRAME_COLOR"])
filtered_seekers_tree_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
filtered_seekers_tree = ttk.Treeview(filtered_seekers_tree_frame, columns=(
    "UserID", "Name", "Email", "Industry", "Location"), show="headings")
filtered_seekers_tree.heading("UserID", text="User ID")
filtered_seekers_tree.heading("Name", text="Name")
filtered_seekers_tree.heading("Email", text="Email")
filtered_seekers_tree.heading("Industry", text="Industry")
filtered_seekers_tree.heading("Location", text="Preferred Location")
filtered_seekers_tree.pack(fill=tk.BOTH, expand=True)

saved_jobs_frame = tk.Frame(seeker_frame, bg=current_colors["FRAME_COLOR"])
saved_jobs_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
tk.Label(saved_jobs_frame, text="Saved Jobs:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).pack(pady=5)
saved_jobs_tree = ttk.Treeview(saved_jobs_frame, columns=(
    "JobID", "Title", "Description", "Industry", "Location"), show="headings")
saved_jobs_tree.heading("JobID", text="Job ID")
saved_jobs_tree.heading("Title", text="Title")
saved_jobs_tree.heading("Description", text="Description")
saved_jobs_tree.heading("Industry", text="Industry")
saved_jobs_tree.heading("Location", text="Location")
saved_jobs_tree.pack(fill=tk.BOTH, expand=True)
update_saved_jobs_tree()

# Tab 4: User Management
user_frame = tk.Frame(notebook, bg=current_colors["FRAME_COLOR"])
notebook.add(user_frame, text="User Management")

tk.Label(user_frame, text="User Management", font=("Arial", 16, "bold"),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["TEXT_COLOR"]).pack(pady=10)

user_frame_inner = tk.Frame(user_frame, bg=current_colors["FRAME_COLOR"])
user_frame_inner.pack(padx=20, pady=10)

tk.Label(user_frame_inner, text="Update User:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(row=0, column=0, columnspan=2, pady=5)
tk.Label(user_frame_inner, text="Email:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=1, column=0, padx=5, pady=5, sticky="e")
email_entry = tk.Entry(user_frame_inner)
email_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Label(user_frame_inner, text="New Name:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=2, column=0, padx=5, pady=5, sticky="e")
name_entry = tk.Entry(user_frame_inner)
name_entry.grid(row=2, column=1, padx=5, pady=5)
tk.Label(user_frame_inner, text="New Phone:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=3, column=0, padx=5, pady=5, sticky="e")
phone_entry = tk.Entry(user_frame_inner)
phone_entry.grid(row=3, column=1, padx=5, pady=5)
tk.Label(user_frame_inner, text="New Password:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=4, column=0, padx=5, pady=5, sticky="e")
password_entry = tk.Entry(user_frame_inner, show="*")
password_entry.grid(row=4, column=1, padx=5, pady=5)
tk.Button(user_frame_inner, text="Update User", command=update_user,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=5, column=0, columnspan=2, pady=5)
tk.Button(user_frame_inner, text="Clear", command=clear_fields,
          bg="#0e3f4f", fg="white").grid(row=6, column=0, columnspan=2, pady=5)

tk.Label(user_frame_inner, text="Delete User:", font=("Arial", 12),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(row=7, column=0, columnspan=2, pady=5)
tk.Label(user_frame_inner, text="Email:", bg=current_colors["FRAME_COLOR"], fg=current_colors["LABEL_COLOR"]).grid(
    row=8, column=0, padx=5, pady=5, sticky="e")
email_entry_delete = tk.Entry(user_frame_inner)
email_entry_delete.grid(row=8, column=1, padx=5, pady=5)
tk.Button(user_frame_inner, text="Delete User", command=delete_user,
          bg=current_colors["BUTTON_COLOR"], fg="white").grid(row=9, column=0, columnspan=2, pady=5)

user_tree_frame = tk.Frame(user_frame, bg=current_colors["FRAME_COLOR"])
user_tree_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
user_tree = ttk.Treeview(user_tree_frame, columns=(
    "UserID", "Name", "Email", "Role"), show="headings")
user_tree.heading("UserID", text="User ID")
user_tree.heading("Name", text="Name")
user_tree.heading("Email", text="Email")
user_tree.heading("Role", text="Role")
user_tree.pack(fill=tk.BOTH, expand=True)
update_user_tree()

# Tab 5: Analytics
analytics_frame = tk.Frame(notebook, bg=current_colors["FRAME_COLOR"])
notebook.add(analytics_frame, text="Analytics")

tk.Label(analytics_frame, text="Analytics Dashboard", font=("Arial", 16, "bold"),
         bg=current_colors["FRAME_COLOR"], fg=current_colors["TEXT_COLOR"]).pack(pady=20)

analytics_buttons_frame = tk.Frame(analytics_frame, bg=current_colors["FRAME_COLOR"])
analytics_buttons_frame.pack(padx=20, pady=10)

tk.Button(analytics_buttons_frame, text="Most Interesting Job", command=most_interesting_job,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=30).grid(row=0, column=0, padx=5, pady=5)
tk.Button(analytics_buttons_frame, text="Jobs with No Applicants Last Month", command=job_no_applicants_last_month,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=30).grid(row=1, column=0, padx=5, pady=5)
tk.Button(analytics_buttons_frame, text="Employer with Max Announcements", command=employer_max_announcements,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=30).grid(row=2, column=0, padx=5, pady=5)
tk.Button(analytics_buttons_frame, text="Employers with No Announcements", command=employers_no_announcements,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=30).grid(row=3, column=0, padx=5, pady=5)
tk.Button(analytics_buttons_frame, text="Available Positions", command=available_positions_last_month,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=30).grid(row=4, column=0, padx=5, pady=5)
tk.Button(analytics_buttons_frame, text="Job Seeker Applications", command=job_seeker_applications,
          bg=current_colors["BUTTON_COLOR"], fg="white", width=30).grid(row=5, column=0, padx=5, pady=5)

# Initially hide all tabs except login
notebook.tab(1, state="normal")
notebook.tab(2, state="disabled")
notebook.tab(3, state="disabled")
notebook.tab(4, state="disabled")
notebook.tab(5, state="disabled")
notebook.select(0)

root.mainloop()