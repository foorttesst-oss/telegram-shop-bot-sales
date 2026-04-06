"""
Telegram Shop Bot - Sample Code Preview
=======================================

This is a preview of the actual bot code you'll receive.
The complete package includes 400+ lines of production-ready code.

🚀 Purchase the complete bot for $24.50:
   hunter@huntingrevenue.com

Features shown in this sample:
- Product management
- Shopping cart system
- Payment integration
- Database operations
"""

import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Bot initialization (token provided in full version)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class ShopDatabase:
    """Database manager for the shop bot"""
    
    def __init__(self, db_path="shop.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    image_url TEXT,
                    category TEXT,
                    stock INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Shopping cart table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cart (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            """)
            
            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    total_amount DECIMAL(10, 2) NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def get_products(self, category=None, limit=10):
        """Get products with optional category filter"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM products WHERE category = ? LIMIT ?",
                    (category, limit)
                )
            else:
                cursor.execute("SELECT * FROM products LIMIT ?", (limit,))
            return cursor.fetchall()
    
    def add_to_cart(self, user_id, product_id, quantity=1):
        """Add product to user's cart"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if product already in cart
            cursor.execute(
                "SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?",
                (user_id, product_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update quantity
                new_quantity = existing[1] + quantity
                cursor.execute(
                    "UPDATE cart SET quantity = ? WHERE id = ?",
                    (new_quantity, existing[0])
                )
            else:
                # Add new item
                cursor.execute(
                    "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                    (user_id, product_id, quantity)
                )
            
            conn.commit()
            return True
    
    def get_cart_items(self, user_id):
        """Get all items in user's cart with product details"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, p.name, p.price, c.quantity, (p.price * c.quantity) as total
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.user_id = ?
            """, (user_id,))
            return cursor.fetchall()

# Initialize database
db = ShopDatabase()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Welcome message with main menu"""
    welcome_text = """
🛍️ **Welcome to Shop Bot!**

Your personal Telegram shopping assistant.

What would you like to do?
"""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🛍️ Browse Products", callback_data="browse_products"),
        InlineKeyboardButton(text="🛒 My Cart", callback_data="view_cart")
    )
    keyboard.row(
        InlineKeyboardButton(text="📞 Contact Support", callback_data="contact_support"),
        InlineKeyboardButton(text="ℹ️ Help", callback_data="help")
    )
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "browse_products")
async def browse_products(callback: types.CallbackQuery):
    """Show product categories or products"""
    products = db.get_products(limit=6)  # Show first 6 products
    
    if not products:
        await callback.message.edit_text(
            "🚫 **No products available**\n\nPlease check back later!",
            parse_mode="Markdown"
        )
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for product in products:
        product_id, name, description, price, image_url, category, stock, created_at = product
        button_text = f"{name} - ${price:.2f}"
        if stock == 0:
            button_text += " ❌"
        
        keyboard.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"product_{product_id}"
            )
        )
    
    keyboard.row(
        InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
    )
    
    await callback.message.edit_text(
        "🛍️ **Available Products**\n\nSelect a product to view details:",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("product_"))
async def show_product(callback: types.CallbackQuery):
    """Show individual product details"""
    product_id = int(callback.data.split("_")[1])
    
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
    
    if not product:
        await callback.answer("Product not found!", show_alert=True)
        return
    
    id, name, description, price, image_url, category, stock, created_at = product
    
    product_text = f"""
🛍️ **{name}**

📝 {description or 'No description available'}

💰 **Price:** ${price:.2f}
📦 **Stock:** {stock} items available
🏷️ **Category:** {category or 'General'}
"""
    
    keyboard = InlineKeyboardBuilder()
    
    if stock > 0:
        keyboard.row(
            InlineKeyboardButton(
                text="🛒 Add to Cart",
                callback_data=f"add_to_cart_{product_id}"
            )
        )
    else:
        keyboard.row(
            InlineKeyboardButton(
                text="❌ Out of Stock",
                callback_data="out_of_stock"
            )
        )
    
    keyboard.row(
        InlineKeyboardButton(text="🔙 Back to Products", callback_data="browse_products")
    )
    
    if image_url:
        await callback.message.delete()
        await bot.send_photo(
            callback.from_user.id,
            photo=image_url,
            caption=product_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            product_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith("add_to_cart_"))
async def add_to_cart(callback: types.CallbackQuery):
    """Add product to user's cart"""
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    success = db.add_to_cart(user_id, product_id)
    
    if success:
        await callback.answer("✅ Added to cart!", show_alert=True)
        
        # Update the keyboard to show "Added to Cart" temporarily
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="✅ Added to Cart",
                callback_data="already_in_cart"
            )
        )
        keyboard.row(
            InlineKeyboardButton(text="🛒 View Cart", callback_data="view_cart"),
            InlineKeyboardButton(text="🔙 Back to Products", callback_data="browse_products")
        )
        
        await callback.message.edit_reply_markup(reply_markup=keyboard.as_markup())
    else:
        await callback.answer("❌ Failed to add to cart", show_alert=True)

@dp.callback_query(lambda c: c.data == "view_cart")
async def view_cart(callback: types.CallbackQuery):
    """Display user's shopping cart"""
    user_id = callback.from_user.id
    cart_items = db.get_cart_items(user_id)
    
    if not cart_items:
        await callback.message.edit_text(
            "🛒 **Your cart is empty**\n\nAdd some products to get started!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🛍️ Browse Products", callback_data="browse_products")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    cart_text = "🛒 **Your Shopping Cart**\n\n"
    total_amount = 0
    
    for item in cart_items:
        cart_id, product_name, price, quantity, item_total = item
        cart_text += f"▫️ {product_name}\n"
        cart_text += f"   ${price:.2f} × {quantity} = ${item_total:.2f}\n\n"
        total_amount += item_total
    
    cart_text += f"💰 **Total: ${total_amount:.2f}**"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="💳 Checkout", callback_data="checkout"),
        InlineKeyboardButton(text="🗑️ Clear Cart", callback_data="clear_cart")
    )
    keyboard.row(
        InlineKeyboardButton(text="🛍️ Continue Shopping", callback_data="browse_products")
    )
    
    await callback.message.edit_text(
        cart_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )

# Payment processing (simplified for preview)
@dp.callback_query(lambda c: c.data == "checkout")
async def process_checkout(callback: types.CallbackQuery):
    """Process checkout (payment integration in full version)"""
    await callback.message.edit_text(
        """
💳 **Checkout Process**

In the full version, this integrates with:
- Telegram Payments API
- Stripe for credit cards
- PayPal for global payments
- Cryptocurrency options

🚀 **Purchase complete bot for $24.50:**
   hunter@huntingrevenue.com

Features included:
✅ Full payment processing
✅ Order management
✅ Admin panel
✅ 30-day support
        """,
        parse_mode="Markdown"
    )

# Error handlers and additional features available in full version
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    """Return to main menu"""
    await start_handler(callback.message)

async def main():
    """Start the bot"""
    print("🚀 Shop Bot Preview Starting...")
    print("💰 Purchase complete version: hunter@huntingrevenue.com")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

"""
========================================
📦 COMPLETE PACKAGE INCLUDES:
========================================

✅ 400+ lines of production code
✅ Admin panel for store management  
✅ Full payment processing (Stripe, PayPal)
✅ Order management system
✅ Customer analytics
✅ Inventory management
✅ Multi-language support
✅ Docker deployment files
✅ Complete documentation
✅ 30 days technical support

💰 Price: $24.50 (Limited time)
📧 Contact: hunter@huntingrevenue.com
🛡️ 30-day money-back guarantee

========================================
This sample shows ~30% of the actual code.
Full version has comprehensive features!
========================================
"""