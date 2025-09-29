from mcp.server.fastmcp import FastMCP
import asyncio
import os
import numpy as np
import matplotlib
from datetime import datetime
import uuid
matplotlib.use('Agg')  # Use non-interactive backend for server environments
import matplotlib.pyplot as plt

# Create MCP server instance
mcp = FastMCP("ChartGenerator")

# Set global color theme for better-looking charts
plt.style.use('seaborn-v0_8')

# Module-level run directory cache so all charts go into one folder per process
RUN_DIR = None

# Ensure charts directory exists
def ensure_charts_directory():
    """Ensure the charts directory exists, create if it doesn't"""
    charts_dir = "media"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
    return charts_dir

# Ensure a unique run directory (timestamp + UUID) exists inside charts directory
def ensure_run_directory() -> str:
    """Create (once) and return one unique subdirectory for this process.

    Folder format: <uuid-with-hyphens>_YYYY-MM-DD_HH-MM-SS
    """
    global RUN_DIR
    if RUN_DIR and os.path.isdir(RUN_DIR):
        return RUN_DIR
    base_dir = ensure_charts_directory()
    run_dir_name = f"{str(uuid.uuid4())}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    RUN_DIR = os.path.join(base_dir, run_dir_name)
    os.makedirs(RUN_DIR, exist_ok=True)
    return RUN_DIR

# Helper function to get full path for saving charts
def get_chart_path(filename: str) -> str:
    """Get the full path for saving a chart in the charts directory"""
    charts_dir = ensure_run_directory()
    # If filename doesn't end with .png, add it
    if not filename.endswith('.png'):
        filename += '.png'
    return os.path.join(charts_dir, filename)

# Register a tool that generates and saves pie charts
@mcp.tool()
async def pie_chart(data: dict, title: str = "Pie Chart", filename: str = "pie_chart.png", colors: list = None) -> str:
    """
    Generate a pie chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each slice. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Create pie chart with custom colors
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Ensure the chart is circular
    ax.axis('equal')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def bar_chart(data: dict, title: str = "Horizontal Bar Chart", filename: str = "bar_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a horizontal bar chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each bar. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Create horizontal bar chart
    bars = ax.barh(labels, values)
    
    # Apply colors to bars
    if colors:
        # Use custom color list
        for i, bar in enumerate(bars):
            bar.set_color(colors[i % len(colors)])
    elif colormap:
        # Use color map for automatic colors
        cmap = plt.cm.get_cmap(colormap)
        for i, bar in enumerate(bars):
            bar.set_color(cmap(i/len(values)))
    # If neither colors nor colormap specified, matplotlib will use default colors
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def area_chart(data: dict, title: str = "Area Chart", filename: str = "area_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate an area chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each area. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Create area chart
    if colors:
        color = colors[0] if colors else None
    elif colormap:
        cmap = plt.cm.get_cmap(colormap)
        color = cmap(0)
    else:
        color = None
    
    ax.fill_between(labels, values, color=color, alpha=0.6)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def line_chart(data: dict, title: str = "Line Chart", filename: str = "line_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a line chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each line. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Create line chart
    if colors:
        color = colors[0] if colors else None
    elif colormap:
        cmap = plt.cm.get_cmap(colormap)
        color = cmap(0)
    else:
        color = None
    
    ax.plot(labels, values, color=color, marker='o', linewidth=2)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def scatter_chart(data: dict, title: str = "Scatter Chart", filename: str = "scatter_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a scatter chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each scatter. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Create scatter chart
    if colors:
        color = colors[0] if colors else None
    elif colormap:
        cmap = plt.cm.get_cmap(colormap)
        color = cmap(0)
    else:
        color = None
    
    ax.scatter(labels, values, color=color, s=100, alpha=0.7)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def box_plot(data: dict, title: str = "Box Plot", filename: str = "box_plot.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a box plot using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each box. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Create box plot
    boxes = ax.boxplot(values, patch_artist=True)
    
    # Apply colors to boxes
    if colors:
        # Use custom color list
        for i, box in enumerate(boxes['boxes']):
            box.set_facecolor(colors[i % len(colors)])
    elif colormap:
        # Use color map for automatic colors
        cmap = plt.cm.get_cmap(colormap)
        for i, box in enumerate(boxes['boxes']):
            box.set_facecolor(cmap(i/len(values)))
    # If neither colors nor colormap specified, matplotlib will use default colors
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def column_chart(data: dict, title: str = "Column Chart", filename: str = "column_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a column chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each column. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file 
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Create column chart
    columns = ax.bar(labels, values)
    
    # Apply colors to columns
    if colors:
        # Use custom color list
        for i, column in enumerate(columns):
            column.set_color(colors[i % len(colors)])
    elif colormap:
        # Use color map for automatic colors
        cmap = plt.cm.get_cmap(colormap)
        for i, column in enumerate(columns):
            column.set_color(cmap(i/len(values)))
    # If neither colors nor colormap specified, matplotlib will use default colors
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def dual_axis_chart(data: dict, title: str = "Dual Axis Chart", filename: str = "dual_axis_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a dual axis chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary containing data for dual axis chart. 
                    Expected format: {"Labels": ["Jan", "Feb", "Mar"], "Series1": [100, 120, 150], "Series2": [20, 25, 30]}
                    OR simple format: {"Jan": 100, "Feb": 120, "Mar": 150}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each series. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax1 = plt.subplots(figsize=(10, 8))
    
    # Check if data has a "Labels" key (complex format) or is simple key-value pairs
    if "Labels" in data:
        # Complex format: {"Labels": ["Jan", "Feb", "Mar"], "Series1": [100, 120, 150], "Series2": [20, 25, 30]}
        labels = data["Labels"]
        series_names = [key for key in data.keys() if key != "Labels"]
        
        if len(series_names) >= 2:
            # Create dual axis chart
            ax2 = ax1.twinx()
            
            # Plot first series on left axis
            series1_values = data[series_names[0]]
            line1 = ax1.plot(labels, series1_values, marker='o', linewidth=2, 
                            label=series_names[0], color=colors[0] if colors else 'blue')
            
            # Plot second series on right axis
            series2_values = data[series_names[1]]
            line2 = ax2.plot(labels, series2_values, marker='s', linewidth=2, 
                            label=series_names[1], color=colors[1] if colors and len(colors) > 1 else 'red')
            
            # Set labels and colors
            ax1.set_xlabel('Period')
            ax1.set_ylabel(series_names[0], color=colors[0] if colors else 'blue')
            ax2.set_ylabel(series_names[1], color=colors[1] if colors and len(colors) > 1 else 'red')
            
            # Add legend
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
        else:
            # Only one series, create simple chart
            series_values = data[series_names[0]]
            ax1.plot(labels, series_values, marker='o', linewidth=2, 
                    label=series_names[0], color=colors[0] if colors else 'blue')
            ax1.set_xlabel('Period')
            ax1.set_ylabel(series_names[0])
            ax1.legend()
    else:
        # Simple format: {"Jan": 100, "Feb": 120, "Mar": 150}
        labels = list(data.keys())
        values = list(data.values())
        
        # Create simple line chart
        ax1.plot(labels, values, marker='o', linewidth=2, 
                color=colors[0] if colors else 'blue')
        ax1.set_xlabel('Period')
        ax1.set_ylabel('Value')
    
    ax1.set_title(title, fontsize=16, fontweight='bold')
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def funnel_chart(data: dict, title: str = "Funnel Chart", filename: str = "funnel_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a funnel chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each funnel section. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Calculate funnel dimensions
    max_value = max(values)
    funnel_width = 0.8  # Width of the funnel
    
    # Create funnel chart by drawing trapezoids
    y_positions = []
    for i, (label, value) in enumerate(zip(labels, values)):
        # Calculate position and width for this section
        y_pos = i
        width = (value / max_value) * funnel_width
        
        # Create trapezoid coordinates
        x_coords = [-width/2, width/2, width/2, -width/2]
        y_coords = [y_pos - 0.3, y_pos - 0.3, y_pos + 0.3, y_pos + 0.3]
        
        # Choose color
        if colors:
            color = colors[i % len(colors)]
        elif colormap:
            cmap = plt.cm.get_cmap(colormap)
            color = cmap(i/len(values))
        else:
            color = None
        
        # Draw the trapezoid
        ax.fill(x_coords, y_coords, color=color, alpha=0.7)
        
        # Add label
        ax.text(0, y_pos, f"{label}: {value}", ha='center', va='center', fontweight='bold')
        
        y_positions.append(y_pos)
    
    # Set up the chart
    ax.set_xlim(-funnel_width/2 - 0.1, funnel_width/2 + 0.1)
    ax.set_ylim(-0.5, len(labels) - 0.5)
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    # Remove axes
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def radar_chart(data: dict, title: str = "Radar Chart", filename: str = "radar_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a radar chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each radar. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis with polar projection
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Calculate angles for each label (evenly spaced around the circle)
    angles = [n / len(labels) * 2 * 3.14159 for n in range(len(labels))]
    
    # Close the plot by appending the first value
    values += values[:1]
    angles += angles[:1]
    
    # Create the radar chart
    if colors:
        color = colors[0] if colors else 'blue'
    elif colormap:
        cmap = plt.cm.get_cmap(colormap)
        color = cmap(0)
    else:
        color = 'blue'
    
    # Plot the radar chart
    ax.plot(angles, values, 'o-', linewidth=2, color=color, markersize=8)
    ax.fill(angles, values, alpha=0.25, color=color)
    
    # Set the labels at the correct angles
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    
    # Set the y-axis limits and labels
    max_value = max(values[:-1])
    ax.set_ylim(0, max_value * 1.1)
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Set title
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def sankey_chart(data: dict, title: str = "Sankey Chart", filename: str = "sankey_chart.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a sankey chart using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each sankey. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Calculate total for percentage calculations
    total = sum(values)
    
    # Set up colors
    if colors:
        color_list = colors
    elif colormap:
        cmap = plt.cm.get_cmap(colormap)
        color_list = [cmap(i/len(values)) for i in range(len(values))]
    else:
        color_list = plt.cm.Set3(np.linspace(0, 1, len(values)))
    
    # Create a simple Sankey-like flow visualization
    # Since matplotlib doesn't have built-in Sankey, we'll create a flow diagram
    
    # Position nodes in two columns
    left_x = 0.1
    right_x = 0.9
    
    # Calculate y positions for left nodes (evenly spaced)
    left_y_positions = np.linspace(0.1, 0.9, len(labels))
    
    # Draw left nodes (source)
    for i, (label, value) in enumerate(zip(labels, values)):
        # Calculate node height based on value proportion
        height = (value / total) * 0.6
        
        # Draw rectangle for node
        rect = plt.Rectangle((left_x - 0.02, left_y_positions[i] - height/2), 
                           0.04, height, 
                           facecolor=color_list[i % len(color_list)], 
                           edgecolor='black', alpha=0.8)
        ax.add_patch(rect)
        
        # Add label
        ax.text(left_x - 0.05, left_y_positions[i], f'{label}\n({value})', 
               ha='right', va='center', fontsize=10, fontweight='bold')
    
    # Draw right nodes (destination) - simplified as bars
    right_y_positions = np.linspace(0.1, 0.9, len(labels))
    
    for i, (label, value) in enumerate(zip(labels, values)):
        # Calculate node height based on value proportion
        height = (value / total) * 0.6
        
        # Draw rectangle for destination node
        rect = plt.Rectangle((right_x - 0.02, right_y_positions[i] - height/2), 
                           0.04, height, 
                           facecolor=color_list[i % len(color_list)], 
                           edgecolor='black', alpha=0.8)
        ax.add_patch(rect)
        
        # Add label
        ax.text(right_x + 0.05, right_y_positions[i], f'{label}\n({value})', 
               ha='left', va='center', fontsize=10, fontweight='bold')
    
    # Draw flow lines between corresponding nodes
    for i, (label, value) in enumerate(zip(labels, values)):
        # Calculate flow width based on value
        flow_width = (value / total) * 0.02
        
        # Draw curved flow line
        x_flow = np.linspace(left_x + 0.02, right_x - 0.02, 50)
        y_flow = np.linspace(left_y_positions[i], right_y_positions[i], 50)
        
        # Add some curve to the flow
        y_flow += 0.02 * np.sin(np.pi * (x_flow - left_x) / (right_x - left_x))
        
        ax.plot(x_flow, y_flow, color=color_list[i % len(color_list)], 
               linewidth=max(1, flow_width * 1000), alpha=0.6)
    
    # Set up the chart
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Remove axes
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Add flow direction indicator
    ax.arrow(0.5, 0.05, 0.2, 0, head_width=0.02, head_length=0.02, 
             fc='gray', ec='gray', alpha=0.7)
    ax.text(0.6, 0.02, 'Flow Direction', ha='center', va='top', 
           fontsize=10, color='gray', alpha=0.7)
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

@mcp.tool()
async def tree_map(data: dict, title: str = "Tree Map", filename: str = "tree_map.png", colors: list = None, colormap: str = None) -> str:
    """
    Generate a tree map using matplotlib and save it as a PNG file.

    Args:
        data (dict): A dictionary of labels and values. Example: {"A": 30, "B": 20, "C": 50}
        title (str): Title of the chart
        filename (str): File name for saving the PNG (will be saved in charts folder)
        colors (list): List of colors for each tree map section. Examples: 
                      ['#FF6B6B', '#4ECDC4', '#45B7D1'] or ['red', 'blue', 'green']
        colormap (str): Color map name for automatic colors. Examples: 'viridis', 'plasma', 'coolwarm', 'Set3'

    Returns:
        str: Path of the saved PNG file
    """
    # Get the full path for saving in charts directory
    filepath = get_chart_path(filename)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Extract labels and values
    labels = list(data.keys())
    values = list(data.values())
    
    # Calculate total for percentage calculations
    total = sum(values)
    
    # Set up colors
    if colors:
        color_list = colors
    elif colormap:
        cmap = plt.cm.get_cmap(colormap)
        color_list = [cmap(i/len(values)) for i in range(len(values))]
    else:
        color_list = plt.cm.Set3(np.linspace(0, 1, len(values)))
    
    # Sort data by values (largest first) for better treemap layout
    sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)
    labels, values = zip(*sorted_data)
    
    # Create a simple treemap visualization
    # Since matplotlib doesn't have built-in treemap, we'll create a hierarchical bar chart
    
    # Calculate positions and widths
    y_positions = np.arange(len(labels))
    bar_widths = [value / total for value in values]
    
    # Create horizontal bars for treemap effect
    bars = ax.barh(y_positions, bar_widths, 
                   color=[color_list[i % len(color_list)] for i in range(len(labels))],
                   alpha=0.8, edgecolor='black', linewidth=1)
    
    # Add value labels inside each bar
    for i, (label, value, bar_width) in enumerate(zip(labels, values, bar_widths)):
        # Calculate position for text
        text_x = bar_width / 2
        text_y = y_positions[i]
        
        # Add label and value
        ax.text(text_x, text_y, f'{label}\n{value}', 
               ha='center', va='center', fontweight='bold', fontsize=10,
               color='white' if i < len(color_list) and color_list[i].startswith('#') and int(color_list[i][1:], 16) < 0x808080 else 'black')
    
    # Set up the chart
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, len(labels) - 0.5)
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Remove axes
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Add percentage labels on the right
    for i, (label, value) in enumerate(zip(labels, values)):
        percentage = (value / total) * 100
        ax.text(1.02, y_positions[i], f'{percentage:.1f}%', 
               ha='left', va='center', fontsize=9, alpha=0.7)
    
    # Save chart to PNG with high DPI
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    # Return the absolute path
    return os.path.abspath(filepath)

# Register a tool to list saved charts
@mcp.tool()
async def list_saved_charts() -> list:
    """
    List all saved chart images in the charts directory.
    
    Returns:
        list: List of PNG chart files in the charts folder
    """
    charts_dir = ensure_charts_directory()
    result = []
    for root, _dirs, files in os.walk(charts_dir):
        for f in files:
            if f.endswith('.png'):
                result.append(os.path.relpath(os.path.join(root, f), charts_dir))
    return sorted(result)

# Register a tool to get charts directory path
@mcp.tool()
async def get_charts_directory() -> str:
    """
    Get the path to the charts directory where all PNG images are stored.
    
    Returns:
        str: Absolute path to the charts directory
    """
    charts_dir = ensure_charts_directory()
    return os.path.abspath(charts_dir)

# Simple Hello World tool for quick verification
@mcp.tool()
async def hello_world() -> str:
    """
    Return a static greeting string to verify the MCP server is responsive.

    Returns:
        str: "Hello World"
    """
    return "Hello World"

if __name__ == "__main__":
    asyncio.run(mcp.run())
