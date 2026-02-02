"""Streamlit frontend for Fashion Finder."""

import os
import base64
from io import BytesIO

import httpx
import streamlit as st
from PIL import Image

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Fashion Finder",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        background: white;
    }
    .price-drop {
        color: #28a745;
        font-weight: bold;
    }
    .price-increase {
        color: #dc3545;
    }
    .shop-badge {
        background: #f0f0f0;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    .item-tag {
        display: inline-block;
        background: #e3f2fd;
        color: #1976d2;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)


def get_user_email():
    """Get user email from session state."""
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    return st.session_state.user_email


def set_user_email(email):
    """Set user email in session state."""
    st.session_state.user_email = email


def call_api(endpoint: str, method: str = "GET", data: dict = None, files: dict = None):
    """Make API call to the backend."""
    url = f"{API_URL}{endpoint}"
    try:
        with httpx.Client(timeout=60.0) as client:
            if method == "GET":
                response = client.get(url, params=data)
            elif method == "POST":
                if files:
                    response = client.post(url, data=data, files=files)
                else:
                    response = client.post(url, json=data)
            elif method == "DELETE":
                response = client.delete(url)
            elif method == "PATCH":
                response = client.patch(url, params=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code >= 400:
                st.error(f"API Error: {response.text}")
                return None
            return response.json()
    except httpx.RequestError as e:
        st.error(f"Connection error: {e}")
        return None


def display_identified_items(items: list):
    """Display identified clothing items."""
    st.subheader("Identified Items")

    selected_items = []
    cols = st.columns(min(len(items), 3)) if items else []

    for idx, item in enumerate(items):
        col = cols[idx % len(cols)]
        with col:
            with st.container():
                st.markdown(f"### {item['item_type'].title()}")
                st.write(item['description'])

                if item.get('brand_guess'):
                    st.write(f"**Brand guess:** {item['brand_guess']}")

                st.write(f"**Color:** {item['color']}")

                if item.get('pattern'):
                    st.write(f"**Pattern:** {item['pattern']}")

                if item.get('material_guess'):
                    st.write(f"**Material:** {item['material_guess']}")

                # Style tags
                if item.get('style_tags'):
                    tags_html = " ".join(
                        f'<span class="item-tag">{tag}</span>'
                        for tag in item['style_tags']
                    )
                    st.markdown(tags_html, unsafe_allow_html=True)

                # Confidence
                confidence = item.get('confidence', 0.8)
                st.progress(confidence, text=f"Confidence: {confidence:.0%}")

                # Size input
                size = st.text_input(
                    "Your size",
                    key=f"size_{idx}",
                    placeholder="e.g., M, 38, 10",
                )

                # Select for search
                if st.checkbox("Include in search", key=f"select_{idx}", value=True):
                    selected_items.append({
                        **item,
                        "size": size,
                    })

                st.divider()

    return selected_items


def display_search_results(results: list, query: str):
    """Display search results with shop comparison."""
    st.subheader(f"Search Results for '{query}'")
    st.write(f"Found {len(results)} products")

    if not results:
        st.info("No products found. Try adjusting your search.")
        return

    # Group by shop for comparison
    by_shop = {}
    for result in results:
        shop_id = result['shop_id']
        if shop_id not in by_shop:
            by_shop[shop_id] = []
        by_shop[shop_id].append(result)

    # Display tabs by shop
    shop_tabs = st.tabs(list(by_shop.keys()) + ["All Results"])

    for idx, (shop_id, shop_results) in enumerate(by_shop.items()):
        with shop_tabs[idx]:
            for product in shop_results[:10]:  # Limit display
                display_product_card(product)

    # All results tab (sorted by total cost)
    with shop_tabs[-1]:
        sorted_results = sorted(
            results,
            key=lambda p: p.get('total_cost_sek') or p['price']
        )
        for product in sorted_results[:20]:
            display_product_card(product)


def display_product_card(product: dict):
    """Display a single product card."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if product.get('image_url'):
            st.image(product['image_url'], width=150)
        else:
            st.write("No image")

    with col2:
        st.markdown(f"### {product['name']}")

        if product.get('brand'):
            st.write(f"**Brand:** {product['brand']}")

        st.markdown(
            f'<span class="shop-badge">{product["shop_name"]}</span>',
            unsafe_allow_html=True
        )

        if product.get('color'):
            st.write(f"**Color:** {product['color']}")

        if product.get('sizes'):
            st.write(f"**Sizes:** {', '.join(product['sizes'][:5])}")

        # Product link
        url = product.get('affiliate_url') or product['product_url']
        st.markdown(f"[View on {product['shop_name']}]({url})")

    with col3:
        # Price display
        price = product['price']
        currency = product['currency']
        st.write(f"**Price:** {price:.2f} {currency}")

        if product.get('original_price') and product['original_price'] > price:
            discount = (1 - price / product['original_price']) * 100
            st.write(f"~~{product['original_price']:.2f}~~ (-{discount:.0f}%)")

        # Total cost breakdown
        if product.get('total_cost_sek'):
            st.write("---")
            st.write("**Total to Sweden:**")
            if product.get('shipping_cost') and product['shipping_cost'] > 0:
                st.write(f"Shipping: {product['shipping_cost']:.2f} {currency}")
            if product.get('customs_cost') and product['customs_cost'] > 0:
                st.write(f"Customs: {product['customs_cost']:.2f} {currency}")
            if product.get('vat_cost') and product['vat_cost'] > 0:
                st.write(f"VAT: {product['vat_cost']:.2f} {currency}")
            st.write(f"**Total: {product['total_cost_sek']:.2f} SEK**")

        # Add to watchlist button
        if st.button("Add to Watchlist", key=f"watch_{product['shop_id']}_{product['external_id']}"):
            add_to_watchlist(product)

    st.divider()


def add_to_watchlist(product: dict):
    """Add a product to the watchlist."""
    email = get_user_email()
    if not email:
        st.warning("Please enter your email in the sidebar to use the watchlist.")
        return

    data = {
        "user_email": email,
        "product_id": product['external_id'],
        "shop_id": product['shop_id'],
        "product_name": product['name'],
        "product_url": product['product_url'],
        "image_url": product.get('image_url'),
        "current_price": product['price'],
        "currency": product['currency'],
        "notify_any_drop": True,
    }

    result = call_api("/api/watchlist", method="POST", data=data)
    if result:
        st.success(f"Added {product['name']} to watchlist!")


def display_watchlist():
    """Display the user's watchlist in sidebar."""
    email = get_user_email()
    if not email:
        st.sidebar.info("Enter your email to view watchlist")
        return

    result = call_api("/api/watchlist", method="GET", data={"user_email": email})
    if not result:
        return

    items = result.get('items', [])
    st.sidebar.subheader(f"Watchlist ({len(items)})")

    for item in items:
        with st.sidebar.expander(item['product_name'][:30] + "..."):
            st.write(f"Shop: {item['shop_id']}")
            st.write(f"Added at: {item['price_at_add']:.2f} {item['currency']}")
            st.write(f"Current: {item['current_price']:.2f} {item['currency']}")

            change = item.get('price_change_percent', 0)
            if change < 0:
                st.markdown(f'<span class="price-drop">{change:.1f}%</span>', unsafe_allow_html=True)
            elif change > 0:
                st.markdown(f'<span class="price-increase">+{change:.1f}%</span>', unsafe_allow_html=True)

            if st.button("Remove", key=f"remove_{item['id']}"):
                call_api(f"/api/watchlist/{item['id']}", method="DELETE")
                st.rerun()


def main():
    """Main application."""
    st.title("👗 Fashion Finder")
    st.write("AI-powered fashion discovery across Swedish & EU shops")

    # Sidebar
    with st.sidebar:
        st.header("Settings")

        # User email
        email = st.text_input(
            "Your Email",
            value=get_user_email(),
            placeholder="you@example.com",
            help="For watchlist and price alerts",
        )
        if email != get_user_email():
            set_user_email(email)

        st.divider()

        # Budget filter
        st.subheader("Budget")
        budget = st.slider("Max total cost (SEK)", 0, 20000, 5000, step=500)

        st.divider()

        # Watchlist
        display_watchlist()

    # Main content - tabs
    tab1, tab2, tab3 = st.tabs(["📸 Identify Outfit", "🔍 Search", "👔 My Outfits"])

    # Tab 1: Image Upload & Identification
    with tab1:
        st.header("Upload Fashion Image")
        st.write("Upload a screenshot or photo to identify clothing items")

        col1, col2 = st.columns([1, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Choose an image",
                type=["jpg", "jpeg", "png", "webp"],
                help="Upload a fashion photo or screenshot",
            )

            image_url = st.text_input(
                "Or paste image URL",
                placeholder="https://example.com/outfit.jpg",
            )

        with col2:
            if uploaded_file:
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", use_container_width=True)
            elif image_url:
                st.image(image_url, caption="Image from URL", use_container_width=True)

        if st.button("🔍 Identify Outfit", type="primary"):
            if uploaded_file:
                # Reset file position
                uploaded_file.seek(0)
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                with st.spinner("Analyzing image with AI..."):
                    result = call_api("/api/identify", method="POST", files=files)
            elif image_url:
                with st.spinner("Analyzing image with AI..."):
                    result = call_api("/api/identify", method="POST", data={"image_url": image_url})
            else:
                st.warning("Please upload an image or provide a URL")
                result = None

            if result:
                st.session_state.identified_items = result.get('items', [])
                st.session_state.outfit_style = result.get('overall_style', '')
                st.session_state.outfit_occasion = result.get('occasion')
                st.session_state.outfit_gender = result.get('gender')

        # Display identified items
        if 'identified_items' in st.session_state and st.session_state.identified_items:
            st.divider()

            # Overall style info
            if st.session_state.get('outfit_style'):
                st.info(f"**Overall Style:** {st.session_state.outfit_style}")

            selected_items = display_identified_items(st.session_state.identified_items)

            # Search button
            if selected_items and st.button("🛍️ Search Selected Items", type="primary"):
                st.session_state.search_items = selected_items
                st.session_state.auto_search = True
                st.info("👉 Switch to the **Search** tab to see results for your items!")
                st.rerun()

    # Tab 2: Search
    with tab2:
        st.header("Search Products")

        # Search form
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            search_query = st.text_input(
                "Search",
                placeholder="e.g., blue wool coat",
                value=st.session_state.get('last_search', ''),
            )

        with col2:
            category = st.selectbox(
                "Category",
                ["All", "Tops", "Bottoms", "Outerwear", "Dresses", "Shoes", "Accessories"],
            )

        with col3:
            gender = st.selectbox(
                "Gender",
                ["All", "Women", "Men", "Unisex", "Kids"],
            )

        col4, col5 = st.columns(2)
        with col4:
            brand = st.text_input("Brand (optional)")
        with col5:
            color = st.text_input("Color (optional)")

        if st.button("🔍 Search", type="primary"):
            if search_query:
                st.session_state.last_search = search_query

                search_data = {
                    "query": search_query,
                    "category": None if category == "All" else category.lower(),
                    "gender": None if gender == "All" else gender.lower(),
                    "brand": brand if brand else None,
                    "color": color if color else None,
                    "max_price": float(budget) if budget < 20000 else None,
                    "limit": 20,
                    "include_costs": True,
                }

                with st.spinner("Searching across shops..."):
                    result = call_api("/api/search", method="POST", data=search_data)

                if result:
                    st.session_state.search_results = result.get('results', [])

        # Display search results
        if 'search_results' in st.session_state:
            display_search_results(st.session_state.search_results, search_query or "items")

        # If we have selected items from identification, search for each
        if 'search_items' in st.session_state and st.session_state.search_items:
            st.divider()
            st.subheader("🎯 Search Results for Identified Items")

            # Auto-search if just came from identification
            auto_search = st.session_state.pop('auto_search', False)

            for idx, item in enumerate(st.session_state.search_items):
                # Build optimized search query from item
                # Start with brand + item type (most important)
                query_parts = []
                if item.get('brand_guess'):
                    query_parts.append(item['brand_guess'])
                query_parts.append(item['item_type'])

                # Add color only if it's specific
                color = item.get('color', '').lower()
                if color and color not in ['unknown', 'multi', 'multicolor', 'various']:
                    # Simplify color (take first if multiple)
                    simple_color = color.split('/')[0].split(',')[0].strip()
                    query_parts.append(simple_color)

                item_query = " ".join(query_parts)

                with st.expander(f"**{item['item_type'].title()}**: {item['description'][:60]}...", expanded=auto_search):
                    st.write(f"**Search query:** {item_query}")
                    if item.get('brand_guess'):
                        st.write(f"**Brand guess:** {item['brand_guess']}")
                    st.write(f"**Color:** {item.get('color', 'N/A')}")

                    # Pass structured data to leverage improved relevance scoring
                    search_data = {
                        "query": item_query,
                        "category": item['item_type'],  # Pass category separately
                        "brand": item.get('brand_guess'),  # Pass brand separately
                        "color": item.get('color') if item.get('color', '').lower() not in ['unknown', 'multi'] else None,
                        "style_tags": item.get('style_tags', []),
                        "size": item.get('size'),
                        "gender": st.session_state.get('outfit_gender'),
                        "max_price": float(budget) if budget < 20000 else None,
                        "limit": 10,
                        "include_costs": True,
                    }

                    # Store results in session state per item
                    result_key = f"item_results_{idx}"

                    if st.button(f"🔍 Search for {item['item_type']}", key=f"search_item_{idx}") or (auto_search and result_key not in st.session_state):
                        with st.spinner(f"Searching for {item['item_type']}..."):
                            result = call_api("/api/search", method="POST", data=search_data)
                        if result:
                            st.session_state[result_key] = result.get('results', [])

                    # Display stored results
                    if result_key in st.session_state:
                        results = st.session_state[result_key]
                        if results:
                            st.write(f"Found **{len(results)}** products:")
                            for product in results[:5]:
                                display_product_card(product)
                        else:
                            st.warning("No products found. Try adjusting the search or check shop feeds.")

            # Clear button
            if st.button("🗑️ Clear All Searches"):
                keys_to_delete = [k for k in st.session_state.keys() if k.startswith('item_results_')]
                for k in keys_to_delete:
                    del st.session_state[k]
                del st.session_state.search_items
                st.rerun()

    # Tab 3: Saved Outfits
    with tab3:
        st.header("My Saved Outfits")

        email = get_user_email()
        if not email:
            st.info("Please enter your email in the sidebar to save and view outfits.")
        else:
            # Save current outfit button
            if 'identified_items' in st.session_state and st.session_state.identified_items:
                if st.button("💾 Save Current Outfit"):
                    outfit_data = {
                        "user_email": email,
                        "name": st.text_input("Outfit Name", value="My Outfit"),
                        "items": [
                            {
                                "item_type": item['item_type'],
                                "description": item['description'],
                                "brand_guess": item.get('brand_guess'),
                                "color": item['color'],
                                "style_tags": item.get('style_tags', []),
                            }
                            for item in st.session_state.identified_items
                        ],
                        "budget": float(budget),
                    }
                    result = call_api("/api/outfits", method="POST", data=outfit_data)
                    if result:
                        st.success("Outfit saved!")

            st.divider()

            # List saved outfits
            result = call_api("/api/outfits", method="GET", data={"user_email": email})
            if result:
                outfits = result.get('outfits', [])
                if not outfits:
                    st.info("No saved outfits yet. Upload an image and save your first outfit!")
                else:
                    for outfit in outfits:
                        with st.expander(f"📦 {outfit['name']}"):
                            st.write(f"Created: {outfit['created_at'][:10]}")
                            if outfit.get('budget'):
                                st.write(f"Budget: {outfit['budget']:.0f} {outfit['budget_currency']}")

                            for item in outfit['items']:
                                st.write(f"- **{item['item_type']}**: {item['description'][:50]}...")

                            if st.button("Delete", key=f"del_outfit_{outfit['id']}"):
                                call_api(f"/api/outfits/{outfit['id']}", method="DELETE")
                                st.rerun()


if __name__ == "__main__":
    main()
