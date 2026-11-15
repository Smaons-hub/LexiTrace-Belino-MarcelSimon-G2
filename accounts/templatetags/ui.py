from django import template

register = template.Library()


@register.filter
def add_class(field, css_classes):
    classes = [field.field.widget.attrs.get('class', ''), css_classes]
    if field.errors:
        classes.append('is-invalid')
    return field.as_widget(attrs={'class': ' '.join(c for c in classes if c)})
