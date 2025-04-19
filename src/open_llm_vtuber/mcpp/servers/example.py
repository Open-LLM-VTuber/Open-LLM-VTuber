from mcp.server.fastmcp import FastMCP

# Optional
# If you want to use some custom environment variables, you can set them here.

__envs__ = {
    "SOMETHING": "ELSE",
}

# Optional
# If you want to set timeout for your server, you can set it here.

from datetime import timedelta
__timeout__ = timedelta(seconds=10)


mcp = FastMCP("My App")

@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI given weight in kg and height in meters"""
    return weight_kg / (height_m**2)


if __name__ == "__main__":

    mcp.run()
