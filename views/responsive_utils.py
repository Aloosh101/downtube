# Responsive Design Utilities

This module includes utility functions for responsive design in web applications.

## Device Detection

def get_device_type(user_agent):
    """Detects the device type based on the user agent string."""
    if 'mobile' in user_agent.lower():
        return 'mobile'
    elif 'tablet' in user_agent.lower():
        return 'tablet'
    else:
        return 'desktop'

## Dynamic Font Sizing

def get_dynamic_font_size(base_size, viewport_width):
    """Calculates dynamic font size based on viewport width."""
    scale_factor = viewport_width / 1440  # Assuming 1440px is the base width
    return base_size * scale_factor

## Mobile-Optimized Layouts

def is_mobile_user(user_agent):
    """Checks if the user is on a mobile device based on user agent."""
    return get_device_type(user_agent) == 'mobile'