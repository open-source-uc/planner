"""
Routes are grouped under this module.
"""

from . import admin, courses, offer, plan, user

routers = [admin.router, courses.router, offer.router, plan.router, user.router]
