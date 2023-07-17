"""
Routes are grouped under this module.
"""

from app.routes import admin, course, offer, plan, user

routers = [admin.router, course.router, offer.router, plan.router, user.router]
