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
    service_name = None  

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
        
        new_data = request.json
        
        
        df_existing = pd.read_csv('goods_gst.csv')

        
        df_new = pd.DataFrame(new_data)

        
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)

        
        df_combined.to_csv('goods_gst.csv', index=False)

        return jsonify({'success': True, 'message': 'New data added successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Route for generating an invoice
@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    try:
        
        company_name = request.form['company_name']
        address = request.form['address']
        city = request.form['city']
        gst = request.form['gst']
        date = request.form['date']
        contact = request.form['contact']
        customer_name = request.form['customer_name']

    
        selected_services = request.form.getlist('services')  # Get multiple services
        original_prices = request.form.getlist('original_prices')  # Get corresponding prices

        
        original_prices = [float(price) for price in original_prices]

        # Create an in-memory PDF file
        buffer = BytesIO()

        
        c = canvas.Canvas(buffer, pagesize=(595, 842), bottomup=0)

        
        c.setFont("Times-Bold", 14)
        c.drawCentredString(300, 40, company_name)  # Centered based on the new width
        c.setFont("Times-Roman", 12)
        c.drawCentredString(300, 60, f"{address}, {city}")
        c.drawCentredString(300, 80, f"GST No: {gst}")
        c.drawCentredString(300, 100, f"Date: {date}")
        c.drawCentredString(300, 120, f"Customer: {customer_name}")
        c.drawCentredString(300, 140, f"Contact: {contact}")


        c.setFont("Times-Bold", 10)
        c.drawString(40, 160, "Service")
        c.drawString(180, 160, "Original Price")
        c.drawString(300, 160, "GST")
        c.drawString(380, 160, "Cess")
        c.drawString(450, 160, "Total")

        
        c.line(40, 165, 550, 165)

        
        y = 180
        total_price = 0
        for service, original_price in zip(selected_services, original_prices):
            service_name = service.capitalize()
            

            if service in gst_data:
                gst_rate = gst_data[service]['Tax (%)']
                cess_rate = gst_data[service].get('Cess (%)', 0)
            else:
                gst_rate = cess_rate = 0  # Default if not found in gst_data

            # Calculate GST, Cess, and Total price for each service
            gst_amount = 2*(original_price * gst_rate) / 100
            gst_rate = gst_amount + original_price
            cess_amount = (gst_rate * cess_rate) / 100
            total = original_price + gst_amount + cess_amount

            
            c.setFont("Times-Roman", 10)
            c.drawString(40, y, service_name[:30])  
            c.drawString(180, y, f"₹{original_price:.2f}")
            c.drawString(300, y, f"₹{gst_amount:.2f}")
            c.drawString(380, y, f"₹{cess_amount:.2f}")
            c.drawString(450, y, f"₹{total:.2f}")

            y += 20  
            total_price += total

        
        c.setFont("Times-Bold", 10)
        c.drawString(300, y + 20, "Total Amount:")
        c.drawString(450, y + 20, f"₹{total_price:.2f}")

        
        c.setFont("Times-Roman", 10)
        c.drawRightString(550, 820, "Signature")


        c.showPage()
        c.save()

        buffer.seek(0)


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
