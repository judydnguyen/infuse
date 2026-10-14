"""
Utility functions with additional dependencies.
"""

import pandas as pd
import matplotlib.pyplot as plt

def process_data(data):
    """Process data using pandas."""
    df = pd.DataFrame(data)
    return df.describe()

def plot_data(data):
    """Plot data using matplotlib."""
    plt.plot(data)
    plt.show()
