-- ============================================================
-- Libralex Information System
-- database/schema.sql
-- Run this once in MySQL Workbench.
-- ============================================================

CREATE DATABASE IF NOT EXISTS libralex_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE libralex_db;

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    user_id          INT             NOT NULL AUTO_INCREMENT,
    username         VARCHAR(80)     NOT NULL UNIQUE,
    password_hash    VARCHAR(255)    NOT NULL,
    email            VARCHAR(255)    NOT NULL UNIQUE,
    role             ENUM('patron','contributor','librarian','admin') NOT NULL DEFAULT 'patron',
    full_name        VARCHAR(150)    NOT NULL,
    contact_number   VARCHAR(30)     NULL,
    date_registered  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active        TINYINT(1)      NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id),
    INDEX idx_users_role     (role),
    INDEX idx_users_username (username)
) ENGINE=InnoDB;

-- 2. BOOKS
CREATE TABLE IF NOT EXISTS books (
    book_id          INT             NOT NULL AUTO_INCREMENT,
    title            VARCHAR(255)    NOT NULL,
    author           VARCHAR(255)    NOT NULL,
    publication_year YEAR            NULL,
    format_type      ENUM('e-book','print','thesis','research paper','other') NOT NULL,
    subject_tags     VARCHAR(500)    NULL,
    abstract         TEXT            NULL,
    file_path        VARCHAR(500)    NULL,
    added_by         INT             NOT NULL,
    date_added       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (book_id),
    INDEX idx_books_format   (format_type),
    INDEX idx_books_year     (publication_year),
    INDEX idx_books_added_by (added_by),
    CONSTRAINT fk_books_added_by
        FOREIGN KEY (added_by) REFERENCES users (user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 3. REVIEWS
CREATE TABLE IF NOT EXISTS reviews (
    review_id    INT          NOT NULL AUTO_INCREMENT,
    book_id      INT          NOT NULL,
    user_id      INT          NOT NULL,
    review_text  TEXT         NOT NULL,
    date_posted  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_approved  TINYINT(1)   NOT NULL DEFAULT 0,
    PRIMARY KEY (review_id),
    UNIQUE KEY uq_review_user_book (user_id, book_id),
    INDEX idx_reviews_book     (book_id),
    INDEX idx_reviews_approved (is_approved),
    CONSTRAINT fk_reviews_book
        FOREIGN KEY (book_id) REFERENCES books (book_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_reviews_user
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 4. SUBMISSIONS
CREATE TABLE IF NOT EXISTS submissions (
    submission_id  INT          NOT NULL AUTO_INCREMENT,
    submitted_by   INT          NOT NULL,
    title          VARCHAR(255) NOT NULL,
    author         VARCHAR(255) NOT NULL,
    abstract       TEXT         NOT NULL,
    file_path      VARCHAR(500) NOT NULL,
    status         ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
    reviewed_by    INT          NULL,
    review_notes   TEXT         NULL,
    date_submitted DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date_reviewed  DATETIME     NULL,
    PRIMARY KEY (submission_id),
    INDEX idx_submissions_status       (status),
    INDEX idx_submissions_submitted_by (submitted_by),
    CONSTRAINT fk_submissions_submitted_by
        FOREIGN KEY (submitted_by) REFERENCES users (user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_submissions_reviewed_by
        FOREIGN KEY (reviewed_by) REFERENCES users (user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 5. SEED: default admin account
-- After setup, create a real admin via the app or a small Python script.
-- This is a placeholder row so the app has at least one admin to log in with.
INSERT IGNORE INTO users
    (username, password_hash, email, role, full_name, date_registered, is_active)
VALUES (
    'admin',
    'placeholder_run_seed_script',
    'admin@libralex.edu',
    'admin',
    'System Administrator',
    NOW(),

);

-- Create the table that tracks user book checkouts
CREATE TABLE IF NOT EXISTS book_borrows (
    borrow_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    user_id INT NOT NULL,
    borrow_date DATETIME NOT NULL,
    due_date DATETIME NOT NULL,
    return_date DATETIME DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'borrowed',
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


