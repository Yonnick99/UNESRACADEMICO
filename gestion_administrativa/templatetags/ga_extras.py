from django import template

register = template.Library()

@register.filter(name="attr")
def attr(obj, field_name):
    if obj is None or not field_name:
        return ""
    return getattr(obj, field_name, "")
