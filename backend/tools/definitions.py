OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the catalog of products based on query or tags. Returns name, price, stock, and description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search in name/description (e.g. 'matte black ink')"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional category tags"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_printer_consumables",
            "description": "Fetch and display the exact compatible inks, media rolls, ribbons, or maintenance supplies for a specific printer model. Use this whenever the customer asks for ink, supplies, paper, or consumables for a printer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "printer_query": {
                        "type": "string",
                        "description": "The printer model name or SKU (e.g. 'Citizen CX-02W', 'Epson SC-P20000', 'SC-P9500', 'Citizen CZ-01')"
                    }
                },
                "required": ["printer_query"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Check the current stock level of a specific product by its ID.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string", "description": "The unique product database ID"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Calculate total price for product quantity with bulk discount rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "The unique product database ID"},
                    "qty": {"type": "integer", "description": "Quantity to order, defaults to 1"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_specs",
            "description": "Retrieve official verified technical specifications, resolution, media sizes, and ink systems for a product model to answer customer queries with 100% accuracy.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string", "description": "The product model name, SKU, or database ID"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_kepler_website",
            "description": "Live scrape product specifications, overview, features, or company details directly from the official Kepler Tech website (https://www.keplertechllc.com) for in-depth information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_or_url": {
                        "type": "string",
                        "description": "The product name, model (e.g. 'SC-P9500', 'Citizen CX-02'), category, or specific Kepler website page URL to fetch."
                    }
                },
                "required": ["query_or_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipping_info",
            "description": "Provide official shipping terms, delivery schedules (Dubai, Abu Dhabi, Northern Emirates, GCC), and free delivery thresholds.",
            "parameters": {
                "type": "object",
                "properties": {"emirate_or_city": {"type": "string", "description": "The customer's Emirate or City (e.g. 'Dubai', 'Abu Dhabi', 'Sharjah')"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_warranty_and_support",
            "description": "Provide official manufacturer warranty terms (12-24 months), on-site installation, and engineering support services.",
            "parameters": {
                "type": "object",
                "properties": {"product_query": {"type": "string", "description": "Optional product or printer model"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "track_order",
            "description": "Check the live fulfillment status and delivery timeline of a quotation or order using the order ID.",
            "parameters": {
                "type": "object",
                "properties": {"order_or_session_id": {"type": "string", "description": "The Order ID or quotation reference"}},
                "required": ["order_or_session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_products",
            "description": "Recommend top 3 popular products from the catalog when customer asks for suggestions.",
            "parameters": {
                "type": "object",
                "properties": {"context": {"type": "string", "description": "Optional context about what the customer wants"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a product to the customer's running cart for this conversation. Use this instead of create_order when the customer is still browsing/adding items across multiple turns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The current chat session ID"},
                    "product_id": {"type": "string", "description": "The product ID to add"},
                    "quantity": {"type": "integer", "description": "Quantity to add, defaults to 1"},
                },
                "required": ["session_id", "product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_cart",
            "description": "Show the customer their current cart contents and total.",
            "parameters": {
                "type": "object",
                "properties": {"session_id": {"type": "string", "description": "The current chat session ID"}},
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Remove a product from the customer's cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The current chat session ID"},
                    "product_id": {"type": "string", "description": "The product ID to remove"},
                },
                "required": ["session_id", "product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkout_cart",
            "description": "Convert the customer's current cart into a real order and generate a payment link. Use this after the cart has items and you have the customer's name and contact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The current chat session ID"},
                    "customer_name": {"type": "string", "description": "Name of the customer"},
                    "customer_contact": {"type": "string", "description": "Customer contact details"},
                },
                "required": ["session_id", "customer_name", "customer_contact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_lead",
            "description": "Save customer details, needs, budget, name, or contact as a CRM lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The current chat session ID"},
                    "name": {"type": "string", "description": "Customer's name"},
                    "contact": {"type": "string", "description": "Customer's phone number or email"},
                    "needs": {"type": "string", "description": "Description of what they want/need"},
                    "budget": {"type": "string", "description": "Their budget (e.g. '500 AED')"},
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create an order directly for the customer, without needing a pre-built cart (single-shot checkout).",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The current chat session ID"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "string"},
                                "quantity": {"type": "integer"},
                            },
                            "required": ["product_id", "quantity"],
                        },
                        "description": "List of products and quantities to order",
                    },
                    "customer_name": {"type": "string", "description": "Name of the customer"},
                    "customer_contact": {"type": "string", "description": "Customer contact details"},
                },
                "required": ["session_id", "items", "customer_name", "customer_contact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_payment_link",
            "description": "Retrieve the checkout link for an existing order.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "The unique Order ID"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Hand over the conversation to a human support rep when the customer is frustrated or has a complex issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The current chat session ID"},
                    "reason": {"type": "string", "description": "Reason for escalation"},
                },
                "required": ["session_id", "reason"],
            },
        },
    },
]
