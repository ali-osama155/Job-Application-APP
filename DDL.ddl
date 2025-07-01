-- Superclass: User
CREATE TABLE "User" (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    Name VARCHAR(100),
    Email VARCHAR(100),
    Phone VARCHAR(20),
    Role INT, -- 0 = Employer, 1 = JobSeeker
    Password VARCHAR(100)
);

-- Subclass: Employer
CREATE TABLE Employer (
    UserID INT PRIMARY KEY,
    ComName VARCHAR(100),
    ComIndustry VARCHAR(100),
    Location VARCHAR(100),
    AnnouncedJobCount INT,
    FOREIGN KEY (UserID) REFERENCES "User"(UserID)
);

-- Subclass: JobSeeker
CREATE TABLE JobSeeker (
    UserID INT PRIMARY KEY,
    ResumeLink VARCHAR(255),
    Industry VARCHAR(100),
    PreferredLocation VARCHAR(100),
    AppliedJobCount INT,
    FOREIGN KEY (UserID) REFERENCES "User"(UserID)
);

-- Skills table
CREATE TABLE Skills (
    SkillID INT IDENTITY(1,1) PRIMARY KEY,
    SkillName VARCHAR(100),
    SkillCategory VARCHAR(100),
    Description TEXT
);

-- JobSeeker-Skills relationship (HasSkills)
CREATE TABLE HasSkills (
    UserID INT,
    SkillID INT,
    EXPYears INT,
    PRIMARY KEY (UserID, SkillID),
    FOREIGN KEY (UserID) REFERENCES JobSeeker(UserID),
    FOREIGN KEY (SkillID) REFERENCES Skills(SkillID)
);

-- Vacancy Job
CREATE TABLE VacancyJob (
    JobID INT IDENTITY(1,1) PRIMARY KEY,
    EmployerID INT,
    Title VARCHAR(100),
    Description TEXT,
    Industry VARCHAR(100),
    Location VARCHAR(100),
    ReqSkill VARCHAR(100),
    EXPRequired INT,
    AppCount INT,
    Status VARCHAR(50),
    FOREIGN KEY (EmployerID) REFERENCES Employer(UserID)
);

-- Application Table
CREATE TABLE Application (
    AppID INT IDENTITY(1,1) PRIMARY KEY,
    JobID INT,
    SeekerID INT,
    Status VARCHAR(50),
    ApplyDate DATE,
    FOREIGN KEY (JobID) REFERENCES VacancyJob(JobID),
    FOREIGN KEY (SeekerID) REFERENCES JobSeeker(UserID)
);

-- Job Application Details (Weak)
CREATE TABLE JobAPPDetail (
    DetailID INT IDENTITY(1,1) PRIMARY KEY,
    AppID INT,
    InterviewDate DATE,
    Comments TEXT,
    FOREIGN KEY (AppID) REFERENCES Application(AppID)
);

-- Saved Vacancy Table
CREATE TABLE SavedVacancy (
    JobID INT,
    SeekerID INT,
    SaveDate DATE,
    PRIMARY KEY (JobID, SeekerID),
    FOREIGN KEY (JobID) REFERENCES VacancyJob(JobID),
    FOREIGN KEY (SeekerID) REFERENCES JobSeeker(UserID)
);
