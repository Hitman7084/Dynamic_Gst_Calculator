from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)

# Load the GST data from the CSV file
def load_gst_data():
    gst_data = {}
    service_category_map = {}
    
    try:
        df = pd.read_csv('goods_gst.csv')

        for _, row in df.iterrows():
            category = str(row['Service Category']).strip().lower() if pd.notna(row['Service Category']) else 'other'
            item = str(row['Service Name']).strip().lower() if pd.notna(row['Service Name']) else 'unknown'

            try:
                gst_rate = float(row['GST Rate'])
            except ValueError:
                gst_rate = 0  # Default to 0% GST if invalid

            try:
                cess_rate = float(row['Cess Rate']) if pd.notna(row['Cess Rate']) else 0
            except ValueError:
                cess_rate = 0  # Default to 0% cess if invalid

            gst_data[item] = {
                'Tax (%)': gst_rate,
                'Cess (%)': cess_rate
            }

            if category not in service_category_map:
                service_category_map[category] = []
            service_category_map[category].append(item)

    except Exception as e:
        print(f"Error loading CSV: {e}")

    return gst_data, service_category_map

gst_data, service_category_map = load_gst_data()

# Route for the index page with the form and table
@app.route('/', methods=['GET', 'POST'])
def index():
    gst_amount = cess_amount = final_price = None
    service_name = None  # Add a variable to hold the item/service name

    if request.method == 'POST':
        original_price = request.form.get('original_price')
        category = request.form.get('category').strip().lower()
        service = request.form.get('service').strip().lower()

        if not original_price.replace('.', '', 1).isdigit():
            error = "Invalid Price!"
            return render_template('index.html', categories=service_category_map.keys(), services=[], gst_data=gst_data, error=error)

        original_price = float(original_price)

        if service not in gst_data:
            error = "Item not found!"
            return render_template('index.html', categories=service_category_map.keys(), services=[], gst_data=gst_data, error=error)

        gst_rate = gst_data[service]['Tax (%)']
        cess_rate = gst_data[service].get('Cess (%)', 0)

        gst_amount = 2 * (original_price * gst_rate) / 100
        gst_price = (original_price + gst_amount)
        cess_amount = (gst_price * cess_rate) / 100 if cess_rate else 0
        final_price = original_price +  gst_amount + cess_amount
        service_name = service.capitalize()  # Capitalize the service/item name

    return render_template('index.html', categories=service_category_map.keys(), services=[], gst_data=gst_data,
                           gst_amount=gst_amount, cess_amount=cess_amount, final_price=final_price, service_name=service_name)


# Dynamic route for getting services based on selected category
@app.route('/get_services/<category>')
def get_services(category):
    category = category.strip().lower()
    services = service_category_map.get(category, [])
    return jsonify(services)

# Route to handle saving of the updated GST data
@app.route('/save_gst_data', methods=['POST'])
def save_gst_data():
    try:
        # Get the new row data from the POST request
        new_data = request.json
        
        # Load the existing CSV data
        df_existing = pd.read_csv('goods_gst.csv')

        # Convert the new data to a DataFrame
        df_new = pd.DataFrame(new_data)

        # Append the new row(s) to the existing DataFrame
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)

        # Save the updated DataFrame back to the CSV
        df_combined.to_csv('goods_gst.csv', index=False)

        return jsonify({'success': True, 'message': 'New data added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Route for generating an invoice
@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    try:
        # Get form data for invoice generation
        company_name = request.form['company_name']
        address = request.form['address']
        city = request.form['city']
        gst = request.form['gst']
        date = request.form['date']
        contact = request.form['contact']
        customer_name = request.form['customer_name']
        authorised_signatory = request.form['authorised_signatory']

        # Create an in-memory PDF file
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(200, 250), bottomup=0)

        # Drawing the invoice using reportlab
        c.setFillColorRGB(0.8, 0.5, 0.7)
        c.line(70, 22, 180, 22)
        c.line(5, 45, 195, 45)
        c.line(15, 120, 185, 120)
        c.line(35, 108, 35, 220)
        c.line(115, 108, 115, 220)
        c.line(135, 108, 135, 220)
        c.line(160, 108, 160, 220)
        c.line(15, 220, 185, 220)

        # Adding company details
        c.setFont("Times-Bold", 10)
        c.drawCentredString(125, 20, company_name)
        c.setFont("Times-Bold", 5)
        c.drawCentredString(125, 30, address)
        c.drawCentredString(125, 35, f"{city}, India")
        c.setFont("Times-Bold", 6)
        c.drawCentredString(125, 42, f"GST No: {gst}")

        # Invoice details
        c.setFont("Times-Bold", 8)
        c.drawCentredString(100, 55, "INVOICE")
        c.setFont("Times-Bold", 5)
        c.drawRightString(70, 70, "Invoice No.:")
        c.drawRightString(100, 70, "XXXXXXX")
        c.drawRightString(70, 80, "Date:")
        c.drawRightString(100, 80, date)
        c.drawRightString(70, 90, "Customer Name:")
        c.drawRightString(100, 90, customer_name)
        c.drawRightString(70, 100, "Phone No.:")
        c.drawRightString(100, 100, contact)

        # Add signature and complete invoice
        c.drawRightString(180, 228, authorised_signatory)
        c.drawRightString(180, 235, "Signature")

        c.showPage()
        c.save()

        buffer.seek(0)

        # Send the generated PDF back to the user for download
        return send_file(buffer, as_attachment=True, download_name="Invoice.pdf", mimetype='application/pdf')

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Route to get the current GST data for display in the table
@app.route('/get_gst_data')
def get_gst_data():
    df = pd.read_csv('goods_gst.csv')
    data = df.to_dict(orient='records')
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
