"""Plotting utilities for football network visualizations."""

import matplotlib.pyplot as plt
from matplotlib.patches import Circle


def draw_football_field(
    ax: plt.Axes,
    linewidth: float = 2,
    alpha: float = 1.0,
    color: str = 'k',
    include_6yard_boxes: bool = True,
    set_limits: bool = True
) -> plt.Axes:
    """
    Draw a football field on the given matplotlib axes.
    
    Uses Wyscout coordinate system (0-100 scale mapped to 105×105 for visualization).
    
    Parameters
    ----------
    ax : plt.Axes
        Matplotlib axes to draw on.
    linewidth : float, default=2
        Width of the field lines.
    alpha : float, default=1.0
        Transparency of the lines (0.0 to 1.0).
    color : str, default='k'
        Color of the field lines.
    include_6yard_boxes : bool, default=True
        Whether to draw the 6-yard goal boxes.
    set_limits : bool, default=True
        Whether to set axis limits and aspect ratio.
        
    Returns
    -------
    plt.Axes
        The axes with the football field drawn.
        
    Examples
    --------
    >>> fig, ax = plt.subplots(figsize=(14, 10))
    >>> draw_football_field(ax)
    >>> ax.scatter(x_coords, y_coords)  # Add your data
    >>> plt.show()
    
    >>> # Semi-transparent field as background
    >>> draw_football_field(ax, alpha=0.5, linewidth=1.5)
    """
    line_kwargs = {'linewidth': linewidth, 'alpha': alpha, 'color': color}
    
    # Outer boundary
    ax.plot([0, 0, 105, 105, 0], [0, 105, 105, 0, 0], **line_kwargs)
    
    # Halfway line
    ax.plot([52.5, 52.5], [0, 105], **line_kwargs)
    
    # Center circle
    center_circle = Circle(
        (52.5, 52.5), 9.15,
        fill=False, edgecolor=color, linewidth=linewidth, alpha=alpha
    )
    ax.add_patch(center_circle)
    
    # Penalty areas (18-yard boxes)
    ax.plot([0, 16.5, 16.5, 0], [21.1, 21.1, 83.9, 83.9], **line_kwargs)  # Left
    ax.plot([105, 88.5, 88.5, 105], [21.1, 21.1, 83.9, 83.9], **line_kwargs)  # Right
    
    # 6-yard boxes (goal areas)
    if include_6yard_boxes:
        ax.plot([0, 5.5, 5.5, 0], [36.8, 36.8, 68.2, 68.2], **line_kwargs)  # Left
        ax.plot([105, 99.5, 99.5, 105], [36.8, 36.8, 68.2, 68.2], **line_kwargs)  # Right
    
    # Set axis properties
    if set_limits:
        ax.set_xlim(-2, 107)
        ax.set_ylim(-2, 107)
        ax.set_aspect('equal')
        ax.grid(False)
    
    return ax
