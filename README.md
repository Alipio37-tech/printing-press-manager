#
# Technologies Used

This project uses the following languages and technologies:

- **Python**: Backend logic and server-side operations (Flask framework)
- **HTML**: Web page templates (with Jinja2)
- **CSS**: Styling for web pages (in `static/css`)
- **JavaScript**: Interactive features and AJAX requests
- **SQL (SQLite)**: Database for storing customers, orders, employees, and users
- **Jinja2**: Templating engine for dynamic HTML rendering in Flask


# Printing Press Management System

## Overview
This is a comprehensive web-based management system for printing press businesses. It streamlines customer, order, employee, and payment management, and provides real-time analytics and reporting.

## Features
- **Customer Management:** Add, edit, and view customer profiles with contact details.
- **Order Management:** Create, update, and track orders for each customer, including service type, amount, payment mode, and status (Paid/Credit/Completed).
- **Payment Tracking:** Easily mark orders as Paid or Credit. Status changes are instantly updated in the database and reflected in the UI.
- **Employee Management:** Add, edit, and remove employees. View total employees on the dashboard.
- **Dashboard:** See key business metrics at a glance: total customers, pending orders, completed orders, credit customers, and employees.
- **Reporting:** Generate detailed system-wide reports, including recent orders and total revenue.
- **Templates:** Intuitive pages for completed orders, paid customers, credit customers, dashboard, and more.
- **Print Functionality:** Print order details and customer lists for record-keeping or sharing.
- **Authentication:** Secure login required for all management features.

## Main Pages & Routes
- **Dashboard:** `/dashboard` — Business overview and metrics.
- **Customers:** `/customers` — Manage customer records.
- **Orders:** `/view_order`, `/completed_orders` — Track and manage orders.
- **Paid Customers:** `/paid_customers` — View all paid orders.
- **Credit Customers:** `/credit_customers` — View all credit orders.
- **Employees:** `/employees` — Manage employees.
- **System Report:** `/system_report` — Full business summary and recent activity.

## Database Structure
- **customers:** Stores customer info (id, name, mobile, email, address).
- **orders:** Stores order info (id, customer_id, service, amount, payment_mode, status, order_date).
- **employees:** Stores employee info (id, name, ...).
- **users:** Stores login credentials.

## Workflow
1. **Login:** Secure authentication is required for all management actions.
2. **Add Customers:** Enter customer details in the Customers page.
3. **Create Orders:** Assign orders to customers, select services, set payment mode and status.
4. **Track Payments:** Mark orders as Paid or Credit. Status is updated via AJAX and reflected in the dashboard and reports.
5. **Manage Employees:** Add or remove employees as needed.
6. **View Dashboard:** Monitor business metrics in real time.
7. **Generate Reports:** Access `/system_report` for a summary of business activity, including recent orders and revenue.
8. **Print Records:** Use print features to generate hard copies of orders or customer lists.

## Getting Started
1. Install Python 3 if not already installed.
2. Open your terminal and run the following command to install all required packages:
	```sh
	pip install -r requirements.txt
	```
3. Run `app.py` to start the server:
	```sh
	python app.py
	```
4. Open your browser and go to `http://localhost:5000/dashboard`.
4. To use the calculator, go to `/service` from the sidebar menu.

## Customization
- Edit HTML templates in the `templates/` folder for branding or layout changes.
- Update CSS and images in the `static/` folder.
- Modify database schema or add new features in `app.py` as needed.

## Security
- All management features require login.
- User sessions are protected with a secret key.

## Support & Further Development
For questions, customization, or feature requests, contact the developer or refer to code comments for guidance. Contributions and suggestions are welcome!
