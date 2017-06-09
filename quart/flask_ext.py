import sys

# This adds a 'fake' set of Flask modules for Flask extensions to use,
# these 'fake' modules however point at the equivalent Quart
# modules. This should allow seamless Flask extension usage.

quart_module = sys.modules['quart']
quart_module.Flask = quart_module.Quart

if 'flask' in sys.modules:
    raise ImportError('Cannot mock flask, already imported')

sys.modules['flask'] = quart_module
flask_modules = {}
for name, module in sys.modules.items():
    if name.startswith('quart.'):
        flask_modules[name.replace('quart.', 'flask.')] = module

sys.modules.update(flask_modules)
