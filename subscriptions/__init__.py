"""
subscriptions - Subscription Management Package (Member 2 Deliverable)
Subscription Management System

Exports managers, dialogs, and GUI views for:
- Products (products.py)
- Plans (plans.py)
- Variants (variants.py)
- Subscriptions (subscriptions.py)
- Unified Hub (hub.py)
"""

from .products import ProductManager, ProductView, ProductFormDialog
from .plans import PlanManager, PlanView, PlanFormDialog
from .variants import VariantManager, VariantView, VariantFormDialog
from .subscriptions import SubscriptionManager, SubscriptionView, SubscriptionWizard, ChangePlanDialog
from .hub import SubscriptionHub

__all__ = [
    'ProductManager',
    'ProductView',
    'ProductFormDialog',
    'PlanManager',
    'PlanView',
    'PlanFormDialog',
    'VariantManager',
    'VariantView',
    'VariantFormDialog',
    'SubscriptionManager',
    'SubscriptionView',
    'SubscriptionWizard',
    'ChangePlanDialog',
    'SubscriptionHub'
]
