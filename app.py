import os
import csv
import json
from datetime import datetime, timedelta
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets configuration
GOOGLE_SHEETS_CREDENTIALS = 'service_account.json'  # Make sure this file exists
GOOGLE_SHEET_NAME = 'Property Inquiries'  # Your Google Sheet name

# Configuration
BOT_TOKEN = "8253938305:AAFUdmflQn4avUjoleVERLr-YuuCAyCfURo"
ADMIN_CHAT_ID = "budhirajaproperties"

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROPERTIES_FILE = os.path.join(BASE_DIR, "properties.csv")
LEADS_FILE = os.path.join(BASE_DIR, "leads.csv")
VISITS_FILE = os.path.join(BASE_DIR, "visits.csv")
RENT_PROPERTIES_FILE = os.path.join(BASE_DIR, "RentProperty.csv")
INQUIRY_FILE = os.path.join(BASE_DIR, "Inquiry.csv")

def save_to_google_sheets(data):
    """Save inquiry data to Google Sheets."""
    try:
        # Set up credentials
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'service_account.json', scope
        )
        client = gspread.authorize(creds)
        
        # Open the Google Sheet
        sheet = client.open('Property Inquiries').sheet1
        
        # Prepare the row data
        row = [
            data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('name', ''),
            data.get('phone', ''),
            data.get('email', ''),
            data.get('message', '').replace('\n', ' '),
            data.get('property_id', ''),
            data.get('chat_id', ''),
            'New'  # Status
        ]
        
        # Append the row
        sheet.append_row(row)
        return True
        
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")
        return False

def handle_inquiry_error(user_id):
    """Handle errors in the inquiry flow."""
    try:
        bot.send_message(
            user_id,
            "❌ An error occurred. Please try again by clicking /start",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
    except Exception as e:
        print(f"Error in handle_inquiry_error: {e}")
# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize Firebase
def init_firebase():
    try:
        # Load the service account key
        with open('serviceAccountKey.json', 'r') as f:
            service_account = json.load(f)
        
        # Initialize Firebase with the service account
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred, {
            'storageBucket': f"{service_account['project_id']}.appspot.com"
        })
        print("✅ Firebase initialized successfully")
        return firestore.client()
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing serviceAccountKey.json: {e}")
        return None
    except FileNotFoundError:
        print("❌ Error: serviceAccountKey.json not found in the project directory")
        return None
    except Exception as e:
        print(f"❌ Firebase initialization error: {e}")
        return None

# Initialize Firebase
db = init_firebase()

# User states for conversation handling
user_states = {}

def set_user_state(user_id, state, data=None):
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id]['state'] = state
    if data:
        user_states[user_id].update(data)

def get_user_state(user_id):
    return user_states.get(user_id, {})

def clear_user_state(user_id):
    if user_id in user_states:
        del user_states[user_id]

# Initialize data files
def init_files():
    # Create properties file if not exists
    if not os.path.exists(PROPERTIES_FILE):
        with open(PROPERTIES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'type', 'purpose', 'title', 'description', 'price',
                'location', 'area', 'bedrooms', 'bathrooms', 'owner_name',
                'owner_contact', 'is_featured', 'created_at', 'images'
            ])
    
    # Create leads file if not exists
    if not os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'name', 'phone', 'property_id', 'message', 'created_at', 'status'
            ])
    
    # Create visits file if not exists
    if not os.path.exists(VISITS_FILE):
        with open(VISITS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'property_id', 'visitor_name', 'visitor_phone',
                'visit_date', 'visit_time', 'status', 'created_at'
            ])
    
    # Create rent properties file if not exists
    if not os.path.exists(RENT_PROPERTIES_FILE):
        with open(RENT_PROPERTIES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'title', 'city', 'type', 'rent_amount', 'security_deposit',
                'bedrooms', 'bathrooms', 'area_size', 'furnishing', 'available_from',
                'lease_duration', 'maintenance_charges', 'seller_name', 'seller_phone',
                'seller_email', 'details'
            ])
    
    # Create inquiry file if not exists
    if not os.path.exists(INQUIRY_FILE):
        with open(INQUIRY_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp', 'Name', 'Mobile', 'Email', 
                'Message', 'Property ID', 'Chat ID', 'Status'
            ])

# Start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    welcome_text = """🏠 *Welcome to Budhiraja Properties!*

Buy, Sell or Rent properties with ease. How can I assist you today?

🕒 *Hours:* Mon-Sat, 10:00 AM - 7:00 PM"""
    
    # Create main menu keyboard
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🏠 Buy Property"),
        types.KeyboardButton("🏢 Rent Property"),
       types.KeyboardButton("📝 Inquiry Now"),
        types.KeyboardButton("📞 Contact Us")
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

# Handle main menu options
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    text = message.text
    user_id = message.chat.id
    
    # Clear any existing state when starting a new command
    clear_user_state(user_id)
    
    if text == "🏠 Buy Property":
        start_property_search(message, "sale")
    elif text == "🏢 Rent Property":
        handle_rent_property(message)
    elif text == "📝 Inquiry Now":
        start_inquiry(message)
    elif text == "📞 Contact Us":
        show_contact_options(message)
    elif text == "🔍 Search Rent Properties":
        show_rent_search_filters(message)
    elif text == "➕ List Property for Rent":
        start_rent_property_listing(message)
    elif text == "🏠 Back to Main Menu":
        send_welcome(message)
    else:
        # If we get an unexpected message, send the welcome message
        send_welcome(message)

# Start property search flow
def start_property_search(message, purpose):
    try:
        user_id = message.chat.id
        set_user_state(user_id, 'awaiting_location', {'purpose': purpose})
        
        # Clear any existing keyboard
        markup = types.ReplyKeyboardRemove()
        
        # Ask for location
        msg = bot.send_message(
            user_id,
            f"📍 Please enter the location (city/area) where you want to {'buy' if purpose == 'sale' else 'rent'} a property:\n\nExample: 'Mumbai', 'South Delhi', 'Whitefield Bangalore'",
            reply_markup=markup
        )
        
        # Register the next step handler
        bot.register_next_step_handler(msg, process_search_location)
        
    except Exception as e:
        print(f"Error in start_property_search: {e}")
        bot.send_message(
            message.chat.id,
            "❌ An error occurred. Please try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

def process_search_location(message):
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Check if user wants to cancel
        if message.text.lower() in ['cancel', '❌ cancel']:
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Validate location input
        location = message.text.strip()
        if not location or len(location) < 2:
            msg = bot.send_message(
                user_id,
                "❌ Please enter a valid location (at least 2 characters).\n\nExample: 'Mumbai', 'South Delhi', 'Whitefield Bangalore'"
            )
            bot.register_next_step_handler(msg, process_search_location)
            return
            
        # Update state with location
        set_user_state(user_id, 'awaiting_property_type', {
            'purpose': state.get('purpose'),
            'filters': {'location': location}
        })
        
        # Show property type options
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        property_types = ["🏡 House", "🏢 Flat", "🏗️ Plot", "🏬 Commercial", "🌾 Farmhouse"]
        markup.add(*property_types)
        markup.add(types.KeyboardButton("❌ Cancel"))
        
        msg = bot.send_message(
            user_id,
            "🏠 What type of property are you looking for?\n\nPlease select one option:",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_search_type)
        
    except Exception as e:
        print(f"Error in process_search_location: {e}")
        bot.send_message(
            message.chat.id,
            "❌ An error occurred. Let's start over.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_search_type(message):
    try:
        user_id = message.chat.id
        
        # Check if user wants to cancel
        if message.text == "❌ Cancel":
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Validate user state
        if user_id not in user_states or 'filters' not in user_states[user_id]:
            bot.send_message(user_id, "⚠️ Session expired. Starting over...")
            send_welcome(message)
            return
            
        # Validate property type
        valid_types = ["🏡 House", "🏢 Flat", "🏗️ Plot", "🏬 Commercial", "🌾 Farmhouse"]
        if message.text not in valid_types:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(*[types.KeyboardButton(t) for t in valid_types] + [types.KeyboardButton("❌ Cancel")])
            
            msg = bot.send_message(
                user_id,
                "❌ Please select a valid property type from the options below:",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, process_search_type)
            return
            
        # Store the selected type (without emoji for consistency)
        type_mapping = {
            "🏡 House": "House",
            "🏢 Flat": "Flat",
            "🏗️ Plot": "Plot",
            "🏬 Commercial": "Commercial",
            "🌾 Farmhouse": "Farmhouse"
        }
        
        user_states[user_id]['filters']['type'] = type_mapping.get(message.text, message.text)
        
        # Ask for maximum price
        markup = types.ForceReply(selective=False)
        msg = bot.send_message(
            user_id,
            "💰 What's your maximum budget? (e.g., 50L, 1Cr, 2.5Cr)\n\nYou can type any budget amount or 'Any' to skip this filter.",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_search_price)
        
    except Exception as e:
        print(f"Error in process_search_type: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

def process_search_price(message):
    try:
        user_id = message.chat.id
        
        # Check if user wants to cancel
        if message.text == "❌ Cancel":
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Validate user state
        if user_id not in user_states or 'filters' not in user_states[user_id]:
            bot.send_message(user_id, "⚠️ Session expired. Starting over...")
            send_welcome(message)
            return
            
        # Store the maximum budget
        user_states[user_id]['filters']['max_budget'] = message.text.strip()
        
        # Ask for minimum area
        markup = types.ForceReply(selective=False)
        msg = bot.send_message(
            user_id,
            "📏 What's the minimum area you're looking for? (e.g., 500 sqft, 1000 sqft, 2000 sqft)\n\nYou can type any area amount or 'Any' to skip this filter.",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_search_area)
        
    except Exception as e:
        print(f"Error in process_search_price: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

def process_search_area(message):
    try:
        user_id = message.chat.id
        
        # Check if user wants to cancel
        if message.text == "❌ Cancel":
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Validate user state
        if user_id not in user_states or 'filters' not in user_states[user_id]:
            bot.send_message(user_id, "⚠️ Session expired. Starting over...")
            send_welcome(message)
            return
            
        # Store the minimum area
        user_states[user_id]['filters']['min_area'] = message.text.strip()
        
        # Perform the search
        properties = search_properties(user_states[user_id]['filters'])
        
        # Show results
        show_property_results(properties, user_id)
        
        # Show options for next steps
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🔄 New Search"),
            types.KeyboardButton("🏠 Main Menu")
        )
        
        msg = bot.send_message(
            user_id,
            "🔍 Search completed! What would you like to do next?",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, handle_search_complete)
        
    except Exception as e:
        print(f"Error in process_search_area: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

def handle_search_complete(message):
    """Handle user action after search results are shown."""
    user_id = message.chat.id
    
    if message.text == "🔄 New Search":
        clear_user_state(user_id)
        send_welcome(message)
    elif message.text == "🏠 Main Menu":
        clear_user_state(user_id)
        send_welcome(message)
    else:
        # If we get an unexpected message, show the welcome message
        clear_user_state(user_id)
        send_welcome(message)

def load_properties():
    """Load properties from the CSV file."""
    properties = []
    try:
        if os.path.exists(PROPERTIES_FILE):
            with open(PROPERTIES_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                properties = list(reader)
    except Exception as e:
        print(f"Error loading properties: {e}")
    return properties

def search_properties(filters):
    """Search properties based on filters."""
    properties = load_properties()
    if not properties:
        return []
    
    filtered_properties = []
    for prop in properties:
        # Filter by city (case-insensitive partial match)
        if 'location' in filters and filters['location'].lower() not in prop.get('city', '').lower():
            continue
            
        # Filter by property type
        if 'type' in filters and filters['type'].lower() != prop.get('type', '').lower():
            continue
            
        # Filter by maximum price (simple comparison for now)
        if 'max_budget' in filters and filters['max_budget'].lower() != 'any':
            try:
                prop_price = float(prop.get('budget', '0').replace(',', '').strip())
                max_price = float(filters['max_budget'].replace('L', '00000').replace('Cr', '0000000').replace(',', ''))
                if prop_price > max_price:
                    continue
            except (ValueError, AttributeError):
                pass
                
        filtered_properties.append(prop)
    
    return filtered_properties

def format_property(prop):
    """Format a property for display with inquiry button and features dropdown."""
    # Format price with commas for better readability
    price = "N/A"
    try:
        price = f"₹{int(float(prop.get('budget', 0))):,}"
    except (ValueError, TypeError):
        price = prop.get('budget', 'N/A')
    
    # Get property details with fallbacks
    property_type = prop.get('type', 'N/A')
    bedrooms = prop.get('bedrooms', 'N/A')
    bathrooms = prop.get('bathrooms', 'N/A')
    area_size = prop.get('area_size', 'N/A')
    details = prop.get('details', 'No additional details available.')
    
    # Define all possible feature categories
    feature_categories = {
        'building_features': '🏢 Building Features',
        'community_features': '🌳 Community & Eco',
        'connectivity_features': '📡 Connectivity & Tech',
        'exterior_features': '🏡 Exterior',
        'interior_features': '🏠 Interior',
        'nearby_features': '📍 Nearby',
        'parking_features': '🅿️ Parking',
        'recreational_features': '🎯 Recreational',
        'security_features': '🔒 Security',
        'structural_features': '🏗️ Structural'
    }
    
    # Build features text
    features_text = ""
    for feature_key, category_name in feature_categories.items():
        features = prop.get(feature_key, '').split('|') if prop.get(feature_key) else []
        if features and any(features):
            features_text += f"\n🔹 *{category_name}:*\n"
            features_text += "• " + "\n• ".join(features) + "\n"
    
    # Format property details
    property_text = f"""
🏢 *{prop.get('title', 'Untitled Property').strip()}*

📍 *Location:* {prop.get('city', 'N/A')}
💰 *Price:* {price}
🏠 *Type:* {property_type}

📏 *Property Details:*
• 🛏️ Bedrooms: {bedrooms}
• 🚿 Bathrooms: {bathrooms}
• 📐 Area: {area_size} sq.ft

✨ *Features:*{features_text}

📝 *Description:*
{details}
"""
    
    # Create inline keyboard with dropdown menu for features
    markup = types.InlineKeyboardMarkup(row_width=2)
    
  
    
    # Add a back button if this is a feature view
    if 'feature_view' in prop:
        markup.add(
            types.InlineKeyboardButton("🔙 Back to Property", 
                                    callback_data=f"property_{prop.get('id')}")
        )
    
    return property_text.strip(), markup

def format_property(prop):
    """Format a property for display."""
    # Format price with commas for better readability
    price = "N/A"
    try:
        price = f"₹{int(float(prop.get('budget', 0))):,}"
    except (ValueError, TypeError):
        price = prop.get('budget', 'N/A')
    
    # Get property details with fallbacks
    property_type = prop.get('type', 'N/A')
    bedrooms = prop.get('bedrooms', 'N/A')
    bathrooms = prop.get('bathrooms', 'N/A')
    area_size = prop.get('area_size', 'N/A')
    details = prop.get('details', 'No additional details available.')
    
    # Format property details with contact information
    property_text = f"""
🏢 *{prop.get('title', 'Untitled Property').strip()}*

📍 *Location:* {prop.get('city', 'N/A')}
💰 *Price:* {price}
🏠 *Type:* {property_type}

📞 *Contact Details:*
- 👤 *Owner:* {prop.get('owner_name', 'N/A')}
- 📱 *Phone:* {prop.get('owner_contact', 'N/A')}

📏 *Property Details:*
- 🛏️ Bedrooms: {bedrooms}
- 🚿 Bathrooms: {bathrooms}
- 📐 Area: {area_size} sq.ft

📝 *Description:*
{details}
"""
    # Create inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=2)
    return property_text.strip(), markup

def show_features_dropdown(property_id, feature_type=None):
    """Show dropdown menu for property features."""
    # Rest of the function...

def show_property_results(properties, user_id):
    """Display search results to the user with inquiry option."""
    if not properties:
        bot.send_message(
            user_id,
            "🔍 No properties found matching your criteria. Try adjusting your search filters.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    
    # Limit the number of results to show
    max_results = 5
    properties_to_show = properties[:max_results]
    
    # Send a header message
    bot.send_message(
        user_id,
        f"✅ Found {len(properties)} properties matching your search:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    # Send each property as a separate message
    for idx, prop in enumerate(properties_to_show, 1):
        try:
            property_text, markup = format_property(prop)
            bot.send_message(
                user_id,
                f"🏠 *Property {idx}/{len(properties_to_show)}*\n{property_text}",
                reply_markup=markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Error showing property: {e}")
            continue  # Skip to next property if there's an error
    
    # Add a footer message if there are more results
    if len(properties) > max_results:
        bot.send_message(
            user_id,
            f"ℹ️ Showing {max_results} of {len(properties)} properties. "
            "Try being more specific with your search to see fewer, more relevant results."
        )
    
    # Add navigation buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔍 New Search"),
        types.KeyboardButton("🏠 Main Menu")
    )
    
    bot.send_message(
        user_id,
        "What would you like to do next?",
        reply_markup=markup
    )

def save_property(property_data):
    """Save property to Firebase"""
    try:
        if not db:
            print("❌ Database not initialized")
            return None
            
        # Add timestamps
        property_data['created_at'] = firestore.SERVER_TIMESTAMP
        property_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        # Add to Firestore
        doc_ref = db.collection('properties').document()
        doc_ref.set(property_data)
        print(f"✅ Property saved to Firebase with ID: {doc_ref.id}")
        return doc_ref.id
        
    except Exception as e:
        print(f"❌ Error saving property to Firebase: {e}")
        return None

def save_visitor(visitor_data):
    """Save visitor details to Firebase"""
    try:
        if not db:
            print("❌ Database not initialized")
            return None
            
        visitor_data['created_at'] = firestore.SERVER_TIMESTAMP
        visitor_data['status'] = 'scheduled'
        
        doc_ref = db.collection('visits').document()
        doc_ref.set(visitor_data)
        print(f"✅ Visit scheduled with ID: {doc_ref.id}")
        return doc_ref.id
        
    except Exception as e:
        print(f"❌ Error saving visitor to Firebase: {e}")
        return None

def save_inquiry(inquiry_data):
    """Save inquiry details to Firebase"""
    try:
        if not db:
            print("❌ Database not initialized")
            return None
            
        inquiry_data['created_at'] = firestore.SERVER_TIMESTAMP
        inquiry_data['status'] = 'new'
        
        doc_ref = db.collection('inquiries').document()
        doc_ref.set(inquiry_data)
        print(f"✅ Inquiry saved with ID: {doc_ref.id}")
        return doc_ref.id
        
    except Exception as e:
        print(f"❌ Error saving inquiry to Firebase: {e}")
        return None

def start_property_listing(message):
    """Start the property listing process."""
    try:
        user_id = message.chat.id
        set_user_state(user_id, 'property_listing', {
            'step': 'type',
            'data': {}
        })
        
        # Ask for property type
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        property_types = ["🏡 House", "🏢 Flat", "🏗️ Plot", "🏬 Commercial", "🌾 Farmhouse"]
        markup.add(*[types.KeyboardButton(pt) for pt in property_types])
        markup.add(types.KeyboardButton("❌ Cancel"))
        
        bot.send_message(
            user_id,
            "🏗️ Let's list your property! First, what type of property is it?\n\n"
            "Please select one option:",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in start_property_listing: {e}")
        bot.send_message(
            message.chat.id,
            "❌ An error occurred. Please try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

def process_property_type(message):
    """Process the selected property type."""
    try:
        user_id = message.chat.id
        property_type = message.text.replace('🏠 ', '').replace('🏢 ', '').replace('🏭 ', '').replace('🏪 ', '').strip()
        
        # Validate property type
        valid_types = ['House', 'Apartment', 'Plot', 'Shop', 'Commercial']
        if property_type not in valid_types:
            msg = bot.reply_to(
                message,
                "❌ Please select a valid property type from the options below:"
            )
            bot.register_next_step_handler(msg, process_property_type)
            return
        
        # Store property type
        user_properties[user_id]['type'] = property_type
        
        # Ask for seller's name
        msg = bot.send_message(
            user_id,
            "👤 *Seller's Name*\n\n"
            "Please enter the property owner's full name:",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        
        bot.register_next_step_handler(msg, process_seller_name)
        
    except Exception as e:
        print(f"Error in process_property_type: {e}")
        bot.reply_to(
            message,
            "❌ An error occurred. Please try again."
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_seller_name(message):
    """Process the seller's name."""
    try:
        user_id = message.chat.id
        seller_name = message.text.strip()
        
        # Validate name (basic validation)
        if len(seller_name) < 2 or len(seller_name) > 50:
            msg = bot.reply_to(
                message,
                "❌ Please enter a valid name (2-50 characters)."
            )
            bot.register_next_step_handler(msg, process_seller_name)
            return
        
        # Store seller's name
        user_properties[user_id]['seller_name'] = seller_name
        
        # Ask for seller's phone number
        msg = bot.send_message(
            user_id,
            "📱 *Contact Number*\n\n"
            "Please enter your 10-digit mobile number (e.g., 9876543210):",
            parse_mode='Markdown'
        )
        
        bot.register_next_step_handler(msg, process_seller_phone)
        
    except Exception as e:
        print(f"Error in process_seller_name: {e}")
        bot.reply_to(
            message,
            "❌ An error occurred. Please try again."
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_seller_phone(message):
    """Process the seller's phone number."""
    try:
        user_id = message.chat.id
        phone = message.text.strip()
        
        # Basic phone number validation (10 digits, numbers only)
        if not (phone.isdigit() and len(phone) == 10):
            msg = bot.reply_to(
                message,
                "❌ Please enter a valid 10-digit mobile number (numbers only)."
            )
            bot.register_next_step_handler(msg, process_seller_phone)
            return
        
        # Store seller's phone
        user_properties[user_id]['seller_phone'] = phone
        
        # Ask for seller's email
        msg = bot.send_message(
            user_id,
            "📧 *Email Address*\n\n"
            "Please enter your email address (optional, but recommended for better reach):",
            parse_mode='Markdown'
        )
        
        bot.register_next_step_handler(msg, process_seller_email)
        
    except Exception as e:
        print(f"Error in process_seller_phone: {e}")
        bot.reply_to(
            message,
            "❌ An error occurred. Please try again."
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_seller_email(message):
    """Process the seller's email (optional)."""
    try:
        user_id = message.chat.id
        email = message.text.strip()
        
        # Basic email validation (optional field)
        if email and ('@' not in email or '.' not in email):
            msg = bot.reply_to(
                message,
                "❌ Please enter a valid email address or send 'skip' to continue without email:",
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(msg, process_seller_email)
            return
        
        # Store seller's email (empty string if not provided)
        user_properties[user_id]['seller_email'] = email if email and email.lower() != 'skip' else ''
        
        # Continue with property title
        msg = bot.send_message(
            user_id,
            "🏷️ *Property Title*\n\n"
            "Enter a descriptive title for your property (e.g., '2BHK Flat in Prime Location'):",
            parse_mode='Markdown'
        )
        
        bot.register_next_step_handler(msg, process_property_title)
        
    except Exception as e:
        print(f"Error in process_seller_email: {e}")
        bot.reply_to(
            message,
            "❌ An error occurred. Please try again."
        )
        clear_user_state(user_id)
        send_welcome(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'property_listing' and 
                                      get_user_state(message.chat.id).get('step') == 'type')
def handle_property_type(message):
    process_property_type(message)

def process_property_title(message):
    """Process the property title."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Validate title
        title = message.text.strip()
        if len(title) < 5:
            msg = bot.send_message(
                user_id,
                "❌ Title is too short. Please enter a descriptive title (at least 5 characters).",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, process_property_title)
            return
            
        # Update state
        state['data']['title'] = title
        state['step'] = 'purpose'
        set_user_state(user_id, state['step'], state['data'])
        
        # Ask for property purpose
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        purposes = ["🏠 For Sale", "🏢 For Rent"]
        markup.add(*[types.KeyboardButton(p) for p in purposes])
        markup.add(types.KeyboardButton("❌ Cancel"))
        
        bot.send_message(
            user_id,
            "🎯 Is this property for sale or rent?",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_title: {e}")
        bot.send_message(
            message.chat.id,
            "❌ An error occurred. Please try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'property_listing' and 
                                      get_user_state(message.chat.id).get('step') == 'title')
def handle_property_title(message):
    process_property_title(message)

def process_property_purpose(message):
    """Process the selected property purpose."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Map to purpose
        purpose_mapping = {
            "🏠 For Sale": "sale",
            "🏢 For Rent": "rent"
        }
        
        purpose = purpose_mapping.get(message.text, '').lower()
        if purpose not in ['sale', 'rent']:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton("🏠 For Sale"),
                types.KeyboardButton("🏢 For Rent")
            )
            
            msg = bot.send_message(
                user_id,
                "❌ Please select a valid option:",
                reply_markup=markup
            )
            return
            
        # Update state
        state['data']['purpose'] = purpose
        state['step'] = 'description'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask for property description
        markup = types.ReplyKeyboardRemove()
        
        bot.send_message(
            user_id,
            "📝 Enter a detailed description of your property. Include key features, amenities, and any other important details:",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_purpose: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'property_listing' and 
                                      get_user_state(message.chat.id).get('step') == 'purpose')
def handle_property_purpose(message):
    process_property_purpose(message)

def process_property_description(message):
    """Process the property description."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Check if user wants to cancel
        if message.text.lower() in ['cancel', '❌ cancel']:
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Update state
        state['data']['description'] = message.text.strip()
        state['step'] = 'price'
        set_user_state(user_id, state['step'], state['data'])
        
        # Ask for property price
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Cancel"))
        
        bot.send_message(
            user_id,
            "💰 Enter the price of your property (e.g., 50L, 1Cr, 2.5Cr):",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_description: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_price(message):
    """Process the property price."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Validate price
        price = message.text.strip()
        if not price:
            msg = bot.send_message(
                user_id,
                "❌ Please enter a valid price (e.g., 50L, 1Cr, 2.5Cr):"
            )
            bot.register_next_step_handler(msg, process_property_price)
            return
            
        # Update state
        state['data']['price'] = price
        state['step'] = 'location'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask for property location
        markup = types.ReplyKeyboardRemove()
        
        bot.send_message(
            user_id,
            "📍 Enter the location of your property (e.g., 'Mumbai', 'South Delhi', 'Whitefield Bangalore'):",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_price: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_location(message):
    """Process the property location."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Validate location
        location = message.text.strip()
        if len(location) < 3:
            msg = bot.send_message(
                user_id,
                "❌ Location is too short. Please enter a valid location (e.g., 'Mumbai', 'South Delhi'):"
            )
            bot.register_next_step_handler(msg, process_property_location)
            return
            
        # Update state
        state['data']['location'] = location
        state['step'] = 'area'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask for property area
        markup = types.ReplyKeyboardRemove()
        
        bot.send_message(
            user_id,
            "📏 Enter the area of your property (e.g., 500 sqft, 1000 sqft, 2000 sqft):",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_location: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_area(message):
    """Process the property area."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Check if user wants to cancel
        if message.text.lower() in ['cancel', '❌ cancel']:
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Update state
        state['data']['area'] = message.text.strip()
        state['step'] = 'bedrooms'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask for property bedrooms
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add(
            types.KeyboardButton("1"),
            types.KeyboardButton("2"),
            types.KeyboardButton("3"),
            types.KeyboardButton("4"),
            types.KeyboardButton("5+")
        )
        
        bot.send_message(
            user_id,
            "🛏️ How many bedrooms does the property have?",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_area: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_bedrooms(message):
    """Process the number of bedrooms."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Validate bedrooms
        bedrooms = message.text.strip()
        if not bedrooms or not any(char.isdigit() for char in bedrooms):
            # Show the bedroom options again
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
            markup.add(
                types.KeyboardButton("1"),
                types.KeyboardButton("2"),
                types.KeyboardButton("3"),
                types.KeyboardButton("4"),
                types.KeyboardButton("5+")
            )
            
            bot.send_message(
                user_id,
                "❌ Please select a valid number of bedrooms:",
                reply_markup=markup
            )
            return
            
        # Update state
        state['data']['bedrooms'] = bedrooms
        state['step'] = 'bathrooms'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask for number of bathrooms
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add(
            types.KeyboardButton("1"),
            types.KeyboardButton("2"),
            types.KeyboardButton("3"),
            types.KeyboardButton("4+")
        )
        
        bot.send_message(
            user_id,
            "🛁 How many bathrooms does the property have?",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_bedrooms: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_bathrooms(message):
    """Process the number of bathrooms."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Validate bathrooms
        bathrooms = message.text.strip()
        if not bathrooms or not any(char.isdigit() for char in bathrooms):
            # Show the bathroom options again
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
            markup.add(
                types.KeyboardButton("1"),
                types.KeyboardButton("2"),
                types.KeyboardButton("3"),
                types.KeyboardButton("4+")
            )
            
            bot.send_message(
                user_id,
                "❌ Please select a valid number of bathrooms:",
                reply_markup=markup
            )
            return
            
        # Update state
        state['data']['bathrooms'] = bathrooms
        state['step'] = 'owner_name'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask for property owner name
        markup = types.ReplyKeyboardRemove()
        
        bot.send_message(
            user_id,
            "� Please enter your name as the property owner:",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_bathrooms: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_owner_name(message):
    """Process the property owner's name."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Validate owner name
        owner_name = message.text.strip()
        if len(owner_name) < 2 or not any(c.isalpha() for c in owner_name):
            msg = bot.send_message(
                user_id,
                "❌ Please enter a valid name (at least 2 letters):"
            )
            bot.register_next_step_handler(msg, process_property_owner_name)
            return
            
        # Update state
        state['data']['owner_name'] = owner_name
        state['step'] = 'owner_contact'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask for owner's contact
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("📱 Share Contact", request_contact=True))
        
        bot.send_message(
            user_id,
            "📞 Please share your contact number or type it manually (e.g., 9876543210):",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_owner_name: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_owner_contact(message):
    """Process the property owner's contact."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Get contact from message or contact sharing
        if message.contact and message.contact.phone_number:
            contact = message.contact.phone_number
            # Remove +91 if present at the beginning
            if contact.startswith('+91'):
                contact = contact[3:]
        else:
            contact = ''.join(filter(str.isdigit, message.text.strip()))
            # Remove +91 if present at the beginning
            if contact.startswith('91') and len(contact) > 10:
                contact = contact[2:]
        
        # Validate contact number (10 digits for Indian numbers)
        if not contact.isdigit() or len(contact) != 10:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("📱 Share Contact", request_contact=True))
            
            msg = bot.send_message(
                user_id,
                "❌ Please enter a valid 10-digit phone number or share your contact:",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, process_property_owner_contact)
            return
        
        # Format the contact number
        formatted_contact = f"+91{contact}"  # Add +91 for Indian numbers
        
        # Update state
        state['data']['owner_contact'] = formatted_contact
        state['step'] = 'is_featured'
        set_user_state(user_id, 'property_listing', state)
        
        # Ask if property is featured
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🔥 Yes, feature this property"),
            types.KeyboardButton("🙅‍♂️ No, don't feature this property")
        )
        
        bot.send_message(
            user_id,
            "🤔 Do you want to feature this property?",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_property_owner_contact: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's try that again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_is_featured(message):
    """Process if property is featured."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Update state
        if message.text == "🔥 Yes, feature this property":
            state['data']['is_featured'] = 'true'
        else:
            state['data']['is_featured'] = 'false'
        
        # Save property
        property_id = save_property_to_database(state['data'])
        
        # Send confirmation
        bot.send_message(
            user_id,
            f"✅ Your property has been listed successfully! Property ID: {property_id}",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Clear state and show welcome
        clear_user_state(user_id)
        send_welcome(message)
        
    except Exception as e:
        print(f"Error in process_property_is_featured: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's start over.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

# Update the main menu handler to use the new property listing flow

def start_inquiry(message, property_id=None):
    """Start the inquiry process for a property."""
    try:
        user_id = message.chat.id
        set_user_state(user_id, 'inquiry', {
            'step': 'name',
            'property_id': property_id,
            'data': {
                'chat_id': str(user_id)  # Store chat_id right away
            }
        })
        
        # Create reply keyboard
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Cancel"))
        
        # Ask for full name directly
        msg = bot.send_message(
            user_id,
            "👤 Please enter your *Full Name*:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_inquiry_name)
    
    except Exception as e:
        print(f"Error in start_inquiry: {e}")
        bot.send_message(
            message.chat.id,
            "❌ An error occurred. Please try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

def process_inquiry_name(message):
    """Process the visitor's name for the inquiry."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        if message.text.lower() in ['cancel', '❌ cancel']:
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Store name and move to next step
        state['data']['name'] = message.text.strip()
        state['step'] = 'phone'
        set_user_state(user_id, 'inquiry', state)
        
        # Ask for phone number
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("📱 Share Contact", request_contact=True),
            types.KeyboardButton("❌ Cancel")
        )
        
        bot.send_message(
            user_id,
            "📱 Please share your mobile number or type it manually (e.g., 9876543210):",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error in process_inquiry_name: {e}")
        handle_inquiry_error(user_id)

def process_inquiry_email(message):
    """Process the visitor's email for the inquiry."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        if message.text and message.text.lower() in ['cancel', '❌ cancel']:
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Basic email validation
        email = message.text.strip()
        if '@' not in email or '.' not in email:
            msg = bot.send_message(
                user_id,
                "❌ Please enter a valid email address (e.g., example@domain.com):"
            )
            bot.register_next_step_handler(msg, process_inquiry_email)
            return
            
        # Store email and move to next step
        state['data']['email'] = email
        state['step'] = 'message'
        set_user_state(user_id, 'inquiry', state)
        
        # Prepare property info if available
        property_info = ""
        if state.get('property_id'):
            property_info = f"\n\n🏠 *Property ID*: {state['property_id']}"
        
        # Ask for message
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Cancel"))
        
        msg = bot.send_message(
            user_id,
            f"💬 Please enter your message or questions about the property:{property_info}\n\n"
            f"ℹ️ *Your Chat ID*: `{user_id}` (automatically included)",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_inquiry_message)
        
    except Exception as e:
        print(f"Error in process_inquiry_email: {e}")
        handle_inquiry_error(user_id)
def process_inquiry_message(message):
    """Process the visitor's message for the inquiry."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        if message.text and message.text.lower() in ['cancel', '❌ cancel']:
            clear_user_state(user_id)
            send_welcome(message)
            return
            
        # Store message
        state['data']['message'] = message.text.strip()
        
        # Prepare inquiry data with all fields
        inquiry_data = {
            'name': state['data'].get('name', ''),
            'phone': state['data'].get('phone', ''),
            'email': state['data'].get('email', ''),
            'message': state['data'].get('message', ''),
            'property_id': state.get('property_id', ''),
            'chat_id': str(user_id),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save to CSV
        csv_success = save_inquiry_to_csv(inquiry_data)
        
        # Save to Google Sheets
        sheets_success = save_to_google_sheets(inquiry_data)
        
        if csv_success or sheets_success:
            # Save to Firebase if available
            if 'db' in globals():
                save_inquiry(inquiry_data)
            
            # Send confirmation to user
            bot.send_message(
                user_id,
                "✅ *Thank you for your inquiry!*\n\n"
                "We've received your message and will get back to you shortly.",
                parse_mode='Markdown',
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            # Send notification to admin
            try:
                admin_message = (
                    f"📩 *New Inquiry Received*\n\n"
                    f"👤 *Name:* {inquiry_data['name']}\n"
                    f"📱 *Mobile:* {inquiry_data['phone']}\n"
                    f"📧 *Email:* {inquiry_data.get('email', 'Not provided')}\n"
                    f"💬 *Message:* {inquiry_data['message']}\n"
                    f"🆔 *Chat ID:* `{user_id}`"
                )
                
                if inquiry_data.get('property_id'):
                    admin_message += f"\n🏠 *Property ID:* {inquiry_data['property_id']}"
                
                bot.send_message(
                    ADMIN_CHAT_ID,
                    admin_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error sending admin notification: {e}")
        else:
            raise Exception("Failed to save inquiry to both CSV and Google Sheets")
        
        # Clear state and show welcome
        clear_user_state(user_id)
        send_welcome(message)
        
    except Exception as e:
        print(f"Error in process_inquiry_message: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred while saving your inquiry. Please try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)
        if save_inquiry_to_csv(inquiry_data):
            # Save to Firebase as well
            try:
                save_inquiry(inquiry_data)  # Pass the inquiry_data dictionary
            except Exception as e:
                print(f"Warning: Could not save to Firebase: {e}")
            
            # Send confirmation to user
            markup = types.ReplyKeyboardRemove()
            bot.send_message(
                user_id,
                "✅ Thank you for your inquiry! We'll get back to you soon.",
                reply_markup=markup
            )
            
            # Prepare admin notification
            admin_message = (
                "📨 *New Inquiry Received*\n\n"
                f"👤 *Name*: {inquiry_data['name']}\n"
                f"📱 *Phone*: {inquiry_data['phone']}\n"
                f"📧 *Email*: {inquiry_data['email']}\n"
                f"💬 *Message*: {inquiry_data['message']}\n"
                f"🆔 *Chat ID*: `{inquiry_data['chat_id']}`\n"
            )
            
            if inquiry_data.get('property_id'):
                admin_message += f"🏠 *Property ID*: {inquiry_data['property_id']}\n"
            
            admin_message += f"\n⏰ *Timestamp*: {inquiry_data['timestamp']}"
            
            # Send notification to admin
            try:
                bot.send_message(
                    ADMIN_CHAT_ID,
                    admin_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error sending admin notification: {e}")
        
        # Clear state and show welcome
        clear_user_state(user_id)
        send_welcome(message)
        
    except Exception as e:
        print(f"Error in process_inquiry_message: {e}")
        handle_inquiry_error(user_id)

# Add message handlers
@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'inquiry' and 
                                      get_user_state(message.chat.id).get('step') == 'email')
def handle_inquiry_email(message):
    process_inquiry_email(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'inquiry' and 
                                      get_user_state(message.chat.id).get('step') == 'message')
def handle_inquiry_message(message):
    process_inquiry_message(message)

def show_contact_options(message):
    """Display contact options to the user."""
    try:
        user_id = message.chat.id
        
        # Create inline keyboard for contact options
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🌐 Visit Website", url="http://budhirajaproperties.in/"),
            types.InlineKeyboardButton("📞 Call Us", callback_data="contact_call")
        )
        markup.add(
            types.InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/917015409306"),
            types.InlineKeyboardButton("📧 Email Us", callback_data="contact_email")
        )
        
        contact_info = """
        📞 *Contact Us*
        
        We're here to help! Choose an option below or visit our website:
        
        • 📞 Call: +91 7015409306
        • 💬 WhatsApp: +91 7015409306
        • 📧 Email: propertiesbudhiraja@gmail.com
        • 🏢 Office: 512/1, Salar Ganj Gate, Panipat-132103 (Haryana)
        • 🕒 Hours: Mon-Sat, 10:00 AM - 7:00 PM
        """
        
        bot.send_message(
            user_id,
            contact_info,
            parse_mode='Markdown',
            reply_markup=markup,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        print(f"Error in show_contact_options: {e}")
        bot.send_message(
            message.chat.id,
            "❌ An error occurred while loading contact options. Please try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)

# Firebase Collection Management
def create_collection(collection_name, document_data):
    """
    Create a new collection in Firestore with an initial document.
    
    Args:
        collection_name (str): Name of the collection to create
        document_data (dict): Data for the initial document
    
    Returns:
        str: Document ID of the created document, or None if failed
    """
    try:
        if not db:
            print("❌ Database not initialized")
            return None
            
        doc_ref = db.collection(collection_name).document()
        doc_ref.set(document_data)
        print(f"✅ Collection '{collection_name}' created with document ID: {doc_ref.id}")
        return doc_ref.id
        
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return None

def get_collection(collection_name):
    """
    Get all documents from a collection.
    
    Args:
        collection_name (str): Name of the collection
        
    Returns:
        list: List of document dictionaries, or empty list if error
    """
    try:
        if not db:
            print("❌ Database not initialized")
            return []
            
        docs = db.collection(collection_name).stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]
    except Exception as e:
        print(f"❌ Error getting collection {collection_name}: {e}")
        return []

# Example admin command handler
@bot.message_handler(commands=['create_collection'])
def handle_create_collection(message):
    """Admin command to create a new collection."""
    try:
        # Basic admin check (you should implement proper admin verification)
        if str(message.chat.username) != ADMIN_CHAT_ID:
            bot.reply_to(message, "❌ Unauthorized. Admin access required.")
            return
            
        # Parse command: /create_collection collection_name
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /create_collection collection_name")
            return
            
        collection_name = parts[1].strip()
        
        # Create collection with a sample document
        doc_id = create_collection(collection_name, {
            'created_at': firestore.SERVER_TIMESTAMP,
            'created_by': message.chat.username,
            'description': f'Sample document for {collection_name} collection'
        })
        
        if doc_id:
            bot.reply_to(message, f"✅ Collection '{collection_name}' created successfully!")
        else:
            bot.reply_to(message, f"❌ Failed to create collection '{collection_name}'")
            
    except Exception as e:
        print(f"Error in handle_create_collection: {e}")
        bot.reply_to(message, "❌ An error occurred while creating the collection.")

# Add this handler for contact option callbacks
@bot.callback_query_handler(func=lambda call: call.data.startswith('contact_'))
def handle_contact_callback(call):
    try:
        user_id = call.message.chat.id
        action = call.data.split('_')[1]
        
        if action == 'call':
            bot.answer_callback_query(call.id, "Calling +91 7015409306")
            bot.send_contact(
                user_id,
                phone_number="+917015409306",
                first_name="Budhiraja",
                last_name="Properties"
            )
            
        elif action == 'whatsapp':
            bot.answer_callback_query(call.id, "Opening WhatsApp...")
            bot.send_message(
                user_id,
                "💬 Chat with us on WhatsApp: https://wa.me/917015409306"
            )
            
        elif action == 'email':
            bot.answer_callback_query(call.id, "Composing email...")
            email = "propertiesbudhiraja@gmail.com"
            subject = "Inquiry from Telegram Bot"
            body = "Hello, I have a question about your properties."
            mailto = f"mailto:{email}?subject={subject}&body={body}"
            bot.send_message(
                user_id,
                f"📧 You can email us at: {email}\n\n"
                f"Or click here to compose an email:\n{mailto}"
            )
            
    except Exception as e:
        print(f"Error in handle_contact_callback: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Please try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('inquiry_'))
def handle_inquiry_callback(call):
    try:
        # Acknowledge the callback to remove the loading state
        bot.answer_callback_query(call.id)
        
        # Extract property ID from callback data
        property_id = call.data.split('_')[1]
        user_id = call.message.chat.id
        
        # Start the inquiry process for this property
        start_inquiry(call.message, property_id=property_id)
        
    except Exception as e:
        print(f"Error handling inquiry callback: {e}")
        try:
            bot.answer_callback_query(
                call.id,
                "❌ Failed to start inquiry. Please try again.",
                show_alert=True
            )
        except Exception as e2:
            print(f"Error sending error message: {e2}")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('feature_', 'features_', 'property_')))
def handle_feature_callback(call):
    try:
        # Acknowledge the callback to remove the loading state
        bot.answer_callback_query(call.id)
        
        data = call.data.split('_')
        action = data[0]
        property_id = data[1]
        
        if action == 'feature':
            # Show specific feature details
            feature_type = data[2]
            text, markup = show_features_dropdown(property_id, feature_type)
            
        elif action == 'features':
            # Show all feature categories
            text, markup = show_features_dropdown(property_id)
            
        elif action == 'property':
            # Show property details
            properties = load_properties()
            prop = next((p for p in properties if str(p.get('id')) == str(property_id)), None)
            if prop:
                text, markup = format_property(prop)
            else:
                text = "❌ Property not found."
                markup = None
        
        if text and markup:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        
    except Exception as e:
        print(f"Error in handle_feature_callback: {e}")
        try:
            bot.answer_callback_query(
                call.id,
                "❌ Failed to load features. Please try again.",
                show_alert=True
            )
        except Exception as e2:
            print(f"Error sending error message: {e2}")

def handle_property_image_upload(message):
    """Handle the property image upload process."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        # Check if user wants to finish uploading
        if message.text and message.text.lower() == '/done':
            # If no images were uploaded, ask again
            if 'images' not in state['data'] or not state['data']['images']:
                msg = bot.send_message(
                    user_id,
                    "⚠️ Please upload at least one photo of your property or send /cancel to exit."
                )
                bot.register_next_step_handler(msg, handle_property_image_upload)
                return
                
            # Move to confirmation step
            return show_property_confirmation(message)
            
        # Check if message contains a photo
        if message.photo:
            # Get the highest resolution photo
            photo = message.photo[-1]
            file_info = bot.get_file(photo.file_id)
            
            # Store the file_id for later use
            if 'images' not in state['data']:
                state['data']['images'] = []
                
            # Check if we've reached the maximum number of images (10)
            if len(state['data']['images']) >= 10:
                bot.send_message(
                    user_id,
                    "⚠️ You've reached the maximum of 10 photos. Processing your listing..."
                )
                return show_property_confirmation(message)
                
            # Add the file_id to our list
            state['data']['images'].append(file_info.file_id)
            
            # Show how many images have been uploaded
            count = len(state['data']['images'])
            remaining = 10 - count
            
            if remaining > 0:
                msg = bot.send_message(
                    user_id,
                    f"✅ Photo {count} received! You can send {remaining} more photos. "
                    f"Send /done when you're finished."
                )
                bot.register_next_step_handler(msg, handle_property_image_upload)
            else:
                bot.send_message(
                    user_id,
                    "✅ You've reached the maximum of 10 photos. Processing your listing..."
                )
                return show_property_confirmation(message)
                
        # If the message is not a photo and not /done, ask for photos again
        else:
            msg = bot.send_message(
                user_id,
                "📸 Please send photos of your property or /done if you've finished uploading."
            )
            bot.register_next_step_handler(msg, handle_property_image_upload)
            
    except Exception as e:
        print(f"Error in handle_property_image_upload: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred while processing your photos. Let's try again.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def show_property_confirmation(message):
    """Show the final confirmation before publishing the property."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        property_data = state['data']
        
        # Prepare confirmation message
        confirmation_text = f"""
✅ *Property Listing Confirmation*\n\n
🏠 *Type:* {property_data.get('type', 'N/A')}
🏠 *Purpose:* {property_data.get('purpose', 'N/A').capitalize()}
💰 *Price:* {property_data.get('price', 'N/A')}
📍 *Location:* {property_data.get('location', 'N/A')}
📏 *Area:* {property_data.get('area', 'N/A')}
🛏️ *Bedrooms:* {property_data.get('bedrooms', 'N/A')}
🚿 *Bathrooms:* {property_data.get('bathrooms', 'N/A')}
👤 *Owner:* {property_data.get('owner_name', 'N/A')}
📞 *Contact:* {property_data.get('owner_contact', 'N/A')}
📸 *Photos:* {len(property_data.get('images', []))} uploaded\n\n
*Description:*
{property_data.get('description', 'N/A')}\n\n
Is this information correct?
"""
        
        # Create confirmation keyboard
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("✅ Yes, Publish Now"),
            types.KeyboardButton("✏️ Edit Details"),
            types.KeyboardButton("❌ Cancel")
        )
        
        msg = bot.send_message(
            user_id,
            confirmation_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_property_confirmation)
        
    except Exception as e:
        print(f"Error in show_property_confirmation: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's start over.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def process_property_confirmation(message):
    """Process the final confirmation of the property listing."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        
        if message.text == "✅ Yes, Publish Now":
            # Save the property to the database
            property_data = state['data']
            
            # Generate a unique ID for the property
            property_id = str(uuid.uuid4())[:8]
            property_data['id'] = property_id
            property_data['user_id'] = user_id
            property_data['timestamp'] = datetime.now().isoformat()
            
            # Save to database (in a real app, you'd use a proper database)
            save_property_to_database(property_data)
            
            # Clear the state
            clear_user_state(user_id)
            
            # Send success message
            bot.send_message(
                user_id,
                f"🎉 *Your property has been listed successfully!*\n\n" \
                f"*Listing ID:* {property_id}\n\n" \
                f"Thank you for using our service. Interested buyers will contact you soon.",
                parse_mode='Markdown',
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            # Show the main menu
            send_welcome(message)
            
        elif message.text == "✏️ Edit Details":
            # Go back to editing details (you can implement this as needed)
            msg = bot.send_message(
                user_id,
                "Which detail would you like to edit?\n" \
                "Please type the field name (e.g., 'title', 'price', 'description'):",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, handle_edit_property_field)
            
        else:  # Cancel or any other input
            clear_user_state(user_id)
            bot.send_message(
                user_id,
                "❌ Property listing cancelled.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            send_welcome(message)
            
    except Exception as e:
        print(f"Error in process_property_confirmation: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's start over.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        clear_user_state(user_id)
        send_welcome(message)

def handle_edit_property_field(message):
    """Handle editing a specific property field."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        field = message.text.strip()
        
        # Map field names to user-friendly names and validation functions
        field_map = {
            'title': ('title', '✏️ Enter the new title:'),
            'price': ('price', '💰 Enter the new price:'),
            'description': ('description', '📝 Enter the new description:'),
            'location': ('location', '📍 Enter the new location:'),
            'area': ('area', '📏 Enter the new area:'),
            'bedrooms': ('bedrooms', '🛏️ Enter the new number of bedrooms:'),
            'bathrooms': ('bathrooms', '🚿 Enter the new number of bathrooms:'),
            'owner name': ('owner_name', '👤 Enter your name:'),
            'contact': ('owner_contact', '📞 Enter your contact number:')
        }
        
        if field in field_map:
            field_key, prompt = field_map[field]
            state['edit_field'] = field_key
            set_user_state(user_id, state['step'], state['data'])
            
            msg = bot.send_message(
                user_id,
                prompt,
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, process_field_edit)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton("✅ Yes, Publish Now"),
                types.KeyboardButton("✏️ Edit Details"),
                types.KeyboardButton("❌ Cancel")
            )
            
            msg = bot.send_message(
                user_id,
                "❌ Invalid field. Please select a field to edit:",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, process_property_confirmation)
            
    except Exception as e:
        print(f"Error in handle_edit_property_field: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's return to confirmation.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        show_property_confirmation(message)

def process_field_edit(message):
    """Process the edited field value."""
    try:
        user_id = message.chat.id
        state = get_user_state(user_id)
        field = state.get('edit_field')
        
        if not field:
            return show_property_confirmation(message)
            
        # Update the field
        state['data'][field] = message.text.strip()
        
        # Clear the edit field
        if 'edit_field' in state:
            del state['edit_field']
            
        set_user_state(user_id, 'property_listing', state)
        
        # Return to confirmation
        show_property_confirmation(message)
        
    except Exception as e:
        print(f"Error in process_field_edit: {e}")
        bot.send_message(
            user_id,
            "❌ An error occurred. Let's return to confirmation.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        show_property_confirmation(message)

def save_property_to_database(property_data):
    """Save property listing to Firebase Firestore, Storage, and properties.csv"""
    try:
        # Get a reference to the Firestore database
        db = firestore.client()
        
        # Create a new document in the 'properties' collection
        doc_ref = db.collection('properties').document()
        
        # Prepare the data to save (excluding images for now)
        property_data_to_save = property_data.copy()
        
        # If there are images, upload them to Firebase Storage
        if 'images' in property_data and property_data['images']:
            storage_client = storage.bucket()
            image_urls = []
            
            for i, file_id in enumerate(property_data['images']):
                try:
                    # Download the photo from Telegram
                    file_info = bot.get_file(file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    
                    # Upload to Firebase Storage
                    blob = storage_client.blob(f"properties/{property_data['id']}/image_{i+1}.jpg")
                    blob.upload_from_string(
                        downloaded_file,
                        content_type='image/jpeg'
                    )
                    
                    # Make the blob publicly viewable
                    blob.make_public()
                    image_urls.append(blob.public_url)
                    
                except Exception as e:
                    print(f"Error uploading image {i+1} for property {property_data['id']}: {e}")
            
            # Add the image URLs to the property data
            property_data_to_save['image_urls'] = image_urls
            
        # Save the property data to Firestore
        doc_ref.set(property_data_to_save)
        print(f"✅ Property {property_data['id']} saved to Firestore")
        
        # Also save to properties.csv
        try:
            property_csv_data = {
                'id': property_data.get('id', ''),
                'type': property_data.get('type', ''),
                'purpose': property_data.get('purpose', ''),
                'title': property_data.get('title', ''),
                'description': property_data.get('description', ''),
                'price': property_data.get('price', ''),
                'location': property_data.get('location', ''),
                'area': property_data.get('area', ''),
                'bedrooms': property_data.get('bedrooms', ''),
                'bathrooms': property_data.get('bathrooms', ''),
                'owner_name': property_data.get('owner_name', ''),
                'owner_contact': property_data.get('owner_contact', ''),
                'user_id': property_data.get('user_id', ''),
                'timestamp': property_data.get('timestamp', ''),
                'status': 'active',
                'image_urls': ';'.join(property_data_to_save.get('image_urls', [])),
                'is_featured': property_data.get('is_featured', 'false')
            }
            
            # Write to CSV file
            file_exists = os.path.isfile('properties.csv')
            with open('properties.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=property_csv_data.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(property_csv_data)
                
            print(f"✅ Property {property_data['id']} saved to properties.csv")
            
        except Exception as e:
            print(f"❌ Error saving property to CSV: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving property to database: {e}")
        return False

# Rent Property Functionality

# Rent Property Functionality

def handle_rent_property(message):
    """Handle rent property menu options"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔍 Search Rent Properties"),
        types.KeyboardButton("🏠 Back to Main Menu")
    )
    bot.send_message(
        message.chat.id,
        "🏢 *Rent Property*\n\nWhat would you like to do?",
        reply_markup=markup,
        parse_mode='Markdown'
    )

def start_rent_property_listing(message):
    pass  # Will be implemented later
def save_rent_property(property_data):
    """Save rent property to CSV"""
    try:
        # Generate unique ID if not exists
        if 'id' not in property_data:
            property_data['id'] = str(uuid.uuid4())
        
        # Prepare the row data in the correct order
        row = [
            property_data.get('id', ''),
            property_data.get('title', ''),
            property_data.get('city', ''),
            property_data.get('type', ''),
            property_data.get('rent_amount', ''),
            property_data.get('security_deposit', ''),
            property_data.get('bedrooms', ''),
            property_data.get('bathrooms', ''),
            property_data.get('area_size', ''),
            property_data.get('furnishing', ''),
            property_data.get('available_from', ''),
            property_data.get('lease_duration', '12 months'),  # Default 12 months
            property_data.get('maintenance_charges', 0),
            property_data.get('seller_name', ''),
            property_data.get('seller_phone', ''),
            property_data.get('seller_email', ''),
            f'"{property_data.get("details", "")}"'
        ]
        
        # Write to CSV
        with open('RentProperty.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
            
        return True, property_data['id']
    except Exception as e:
        print(f"Error saving rent property: {e}")
        return False, str(e)

def search_rent_properties(filters=None):
    """Search rent properties based on filters"""
    try:
        properties = []
        with open('RentProperty.csv', 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # If no filters, return all
                if not filters:
                    properties.append(row)
                    continue
                    
                # Apply filters
                match = True
                for key, value in filters.items():
                    if key in row and value and str(row[key]).lower() != str(value).lower():
                        match = False
                        break
                
                if match:
                    properties.append(row)
        
        return properties
    except Exception as e:
        print(f"Error searching rent properties: {e}")
        return []

def show_rent_property_listings(chat_id, properties):
    """Display rent property listings"""
    if not properties:
        bot.send_message(chat_id, "No properties found matching your criteria.")
        return
    
    for prop in properties:
        # Format property details
        details = (
            f"🏠 *{prop.get('title', 'N/A')}*\n"
            f"📍 *Location:* {prop.get('city', 'N/A')}\n"
            f"🏡 *Type:* {prop.get('type', 'N/A')}\n"
            f"💰 *Rent:* ₹{prop.get('rent_amount', 'N/A')}/month\n"
            f"🛌 *Bedrooms:* {prop.get('bedrooms', 'N/A')} | 🚿 *Bathrooms:* {prop.get('bathrooms', 'N/A')}\n"
            f"📏 *Area:* {prop.get('area_size', 'N/A')} sq.ft\n"
            f"🛋️ *Furnishing:* {prop.get('furnishing', 'N/A')}\n"
            f"📅 *Available From:* {prop.get('available_from', 'N/A')}\n"
            f"🔑 *Security Deposit:* ₹{prop.get('security_deposit', 'N/A')}\n"
            f"📝 *Details:* {prop.get('details', 'N/A')}\n"
            f"👤 *Contact:* {prop.get('seller_name', 'N/A')} - {prop.get('seller_phone', 'N/A')}"
        )
        
        # Create inline keyboard for actions
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📞 Contact Owner", callback_data=f"contact_{prop['id']}"),
            InlineKeyboardButton("📅 Schedule Visit", callback_data=f"visit_{prop['id']}")
        )
        
        # Send property details
        bot.send_message(
            chat_id,
            details,
            reply_markup=markup,
            parse_mode='Markdown'
        )

def show_rent_search_filters(message):
    """Show search filters for rent properties"""
    user_id = message.chat.id
    set_user_state(user_id, 'rent_search_city')
    
    msg = bot.send_message(
        user_id,
        "🔍 *Search Rent Properties*\n\n"
        "Enter city to search in (or type 'all' to see all properties):",
        parse_mode='Markdown',
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_rent_search_city)

def process_rent_search_city(message):
    """Process city filter for rent property search"""
    if message.text.lower() in ['cancel', 'back']:
        return send_welcome(message)
        
    user_id = message.chat.id
    city = None if message.text.lower() == 'all' else message.text
    
    # Search properties with city filter
    filters = {'city': city} if city else {}
    properties = search_rent_properties(filters)
    
    if not properties:
        bot.send_message(
            user_id,
            "No properties found in the specified location. Try a different city or check back later.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return handle_rent_property(message)
    
    # Show the properties
    show_rent_property_listings(user_id, properties)
    handle_rent_property(message)  # Show menu again

@bot.callback_query_handler(func=lambda call: call.data.startswith(('contact_', 'visit_')))
def handle_rent_property_actions(call):
    """Handle rent property actions (contact, visit)"""
    user_id = call.message.chat.id
    action, property_id = call.data.split('_', 1)
    
    if action == 'contact':
        # Get property details
        properties = search_rent_properties({'id': property_id})
        if properties:
            prop = properties[0]
            contact_info = (
                f"📞 *Contact Owner*\n\n"
                f"🏠 *Property:* {prop.get('title', 'N/A')}\n"
                f"👤 *Owner:* {prop.get('seller_name', 'N/A')}\n"
                f"📱 *Phone:* {prop.get('seller_phone', 'N/A')}\n"
                f"📧 *Email:* {prop.get('seller_email', 'N/A')}"
            )
            bot.send_message(user_id, contact_info, parse_mode='Markdown')
    
    elif action == 'visit':
        # Start visit scheduling process
        set_user_state(user_id, 'schedule_visit', {'property_id': property_id})
        bot.send_message(
            user_id,
            "📅 *Schedule a Visit*\n\n"
            "Please enter your preferred date and time for the visit (e.g., 'Tomorrow 4 PM' or '15 Aug 3:30 PM'):",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(call.message, process_visit_schedule)

def process_visit_schedule(message):
    """Process visit schedule request"""
    if message.text.lower() in ['cancel', 'back']:
        return handle_rent_property(message)
        
    user_id = message.chat.id
    state = get_user_state(user_id)
    property_id = state.get('property_id')
    
    if not property_id:
        return handle_rent_property(message)
    
    # Get property details
    properties = search_rent_properties({'id': property_id})
    if not properties:
        return bot.send_message(user_id, "❌ Property not found.")
    
    prop = properties[0]
    
    # Save visit request
    visit_data = {
        'id': str(uuid.uuid4()),
        'property_id': property_id,
        'property_title': prop.get('title', 'N/A'),
        'visitor_id': user_id,
        'visitor_name': message.from_user.first_name,
        'visit_date': message.text,
        'status': 'pending',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Save to visits file
    try:
        with open('visits.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                visit_data['id'],
                visit_data['property_id'],
                visit_data['property_title'],
                visit_data['visitor_id'],
                visit_data['visitor_name'],
                visit_data['visit_date'],
                visit_data['status'],
                visit_data['created_at']
            ])
        
        # Notify user
        bot.send_message(
            user_id,
            f"✅ Visit request submitted!\n\n"
            f"*Property:* {prop.get('title', 'N/A')}\n"
            f"*Requested Time:* {message.text}\n\n"
            f"The property owner will contact you shortly to confirm the visit.",
            parse_mode='Markdown'
        )
        
        # Notify admin (if configured)
        if ADMIN_CHAT_ID:
            admin_msg = (
                "🔔 *New Visit Request*\n\n"
                f"*Property:* {prop.get('title', 'N/A')}\n"
                f"*Requested Time:* {message.text}\n"
                f"*Visitor:* {message.from_user.first_name} (@{message.from_user.username or 'N/A'})\n"
                f"*Contact:* {message.from_user.id}"
            )
            bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode='Markdown')
            
    except Exception as e:
        print(f"Error saving visit request: {e}")
        bot.send_message(
            user_id,
            "❌ Failed to submit visit request. Please try again later."
        )
    
    # Return to rent property menu
    handle_rent_property(message)
# Add message handlers for the inquiry flow
@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'inquiry' and 
                                  get_user_state(message.chat.id).get('step') == 'name')
def handle_inquiry_name(message):
    process_inquiry_name(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'inquiry' and 
                                  get_user_state(message.chat.id).get('step') == 'phone')
def handle_inquiry_phone(message):
    process_inquiry_phone(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'inquiry' and 
                                  get_user_state(message.chat.id).get('step') == 'message')
def handle_inquiry_message(message):
    process_inquiry_message(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).get('state') == 'inquiry' and 
                                  get_user_state(message.chat.id).get('step') == 'email')
def handle_inquiry_email(message):
    process_inquiry_email(message)
# Initialize the bot
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    init_files()
    print("✅ Data files initialized")
    print("🤖 Bot is running...")
    bot.polling(none_stop=True)


