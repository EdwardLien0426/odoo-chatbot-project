{
    'name': 'Website LLM Chat',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Public chatbot powered by RocketRide AI',
    'depends': ['website', 'hr'],
    'data': ['views/templates.xml', 'views/menu.xml'],
    'assets': {
        'web.assets_frontend': [
            'website_llm_chat/static/src/css/chatbot.css',
            'website_llm_chat/static/src/js/chatbot.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
