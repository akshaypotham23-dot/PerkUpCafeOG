# PerkUpCafé — Setup Guide

## Project Structure
```
perkupcafe/
├── app.py                   ← Flask backend (updated)
├── config.py                ← DB credentials
├── hash.py                  ← Admin password hash utility
├── templates/
│   ├── home.html            ← ✨ NEW: Public landing page (default route)
│   ├── login.html           ← /login — standalone login page
│   ├── signup.html          ← /signup — standalone signup page
│   ├── index.html           ← /dashboard — customer dashboard (login required)
│   ├── admin.html           ← /admin — admin panel (admin role required)
│   └── payment.html         ← /payment — checkout (login required)
└── static/
    ├── CSS/
    │   └── Style.css        ← Master stylesheet (updated with cart/profile styles)
    └── JavaScript/
        ├── Auth.js          ← Login & signup logic
        ├── Cart.js          ← Cart logic (updated: login prompt on checkout)
        └── Dashboard.js     ← Session check & section navigation
```

## Setup
1. Install dependencies:
   ```
   pip install flask flask-mysqlclient bcrypt mysql-connector-python
   ```
2. Update `config.py` with your MySQL credentials
3. Create the database and run your SQL schema
4. To create an admin password hash: `python hash.py`
5. Run: `python app.py`
6. Visit: http://localhost:5000

---

## Key Changes in This Version

### 🏠 Public Home Page (home.html)
- The website now **opens with a beautiful public landing page** at `/`
- Visitors can browse without creating an account
- Sections: Hero, Menu Preview, Categories, How It Works, About, Testimonials, CTA, Contact
- **Sign In / Create Account modal** is embedded directly in the home page
- Smooth scrolling navigation with sticky top navbar

### 🔐 Login Flow
- Users can browse the site freely as guests
- **Cart:** Clicking "Add to Cart" as a guest shows a friendly login prompt
- **Checkout:** Clicking "Checkout" as a guest shows a login/signup prompt
- Login and Signup are accessible via the top-right "Sign In" button or inline CTA buttons
- The login modal supports: Sign In, Create Account tabs + Forgot Password flow

### 📋 Route Changes
| Route | Before | After |
|-------|--------|-------|
| `/` | Login page (redirect if logged in) | **Public home page** (redirect to dashboard if logged in) |
| `/login` | Login page | Login page (standalone) |
| `/dashboard` | Customer dashboard | Customer dashboard (redirect to home if not logged in) |
| `/payment` | Redirect to login | **Redirect to home** (not login page) |

---

## Features

### Public (home.html — no login needed)
- Full landing page with hero, menu preview, about, testimonials, contact
- Category showcase
- Sign In modal with login, signup, forgot password
- Smooth scroll navigation

### Customer (index.html — after login)
- Browse 24 menu items across 6 categories
- Click any item → description popup + Add to Cart
- Category filter pills
- Cart with qty controls + checkout
- Order history with live status (auto-refreshes every 5s)
- Profile page with delivery address management

### Admin (admin.html — admin role only)
- Orders — KPI cards, filter by status, search, update status
- Menu Management — toggle availability, add/remove items
- Inventory — stock levels with visual bars, low-stock alerts
- Promotions — active coupons, loyalty programme leaderboard
- Delivery Zones — manage areas, fees, delivery times
- Customers — full customer table with search
- Reviews — recent reviews + rating distribution chart
- Staff — team roster with roles
- Push Notifications — send broadcast messages

---

## SQL Schema (reference)
```sql
CREATE DATABASE perkupcafe;
USE perkupcafe;

CREATE TABLE users (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(100) NOT NULL,
  email      VARCHAR(150) UNIQUE NOT NULL,
  password   VARCHAR(255) NOT NULL,
  role       ENUM('user','admin') DEFAULT 'user',
  address    TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  price        DECIMAL(8,2) NOT NULL,
  is_available TINYINT(1) DEFAULT 1,
  category     VARCHAR(50) DEFAULT 'Hot Coffee',
  emoji        VARCHAR(10) DEFAULT '☕',
  description  TEXT
);

CREATE TABLE cart (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  product_id INT NOT NULL,
  quantity   INT DEFAULT 1,
  FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  UNIQUE KEY uq_user_product (user_id, product_id)
);

CREATE TABLE orders (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL,
  status       ENUM('Pending','Preparing','Out for Delivery','Completed','Cancelled') DEFAULT 'Pending',
  order_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE order_items (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  order_id   INT NOT NULL,
  product_id INT NOT NULL,
  quantity   INT NOT NULL,
  price      DECIMAL(8,2) NOT NULL,
  FOREIGN KEY (order_id)   REFERENCES orders(id)   ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id)
);
```
