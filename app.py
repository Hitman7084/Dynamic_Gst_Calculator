from flask import Flask, render_template, request, jsonify
import pandas as pd

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

        gst_amount = (original_price * gst_rate) / 100
        cess_amount = (original_price * cess_rate) / 100 if cess_rate else 0
        final_price = original_price + 2 * gst_amount + cess_amount
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
        updated_data = request.json
        df = pd.DataFrame(updated_data)
        df.to_csv('goods_gst.csv', index=False)
        return jsonify({'success': True, 'message': 'Data saved successfully!'})
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
