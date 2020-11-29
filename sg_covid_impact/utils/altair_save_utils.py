from altair_saver import save
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import os

import sg_covid_impact

project_dir = sg_covid_impact.project_dir

FIG_PATH = f"{project_dir}/figures"

# Checks if the right paths exist and if not creates them when imported
if not os.path.exists(f"{FIG_PATH}/png"):
    os.mkdir(f"{FIG_PATH}/png")

if not os.path.exists(f"{FIG_PATH}/html"):
    os.mkdir(f"{FIG_PATH}/html")


def altair_visualisation_setup():
    # Set up the driver to save figures as png
    driver = webdriver.Chrome(ChromeDriverManager().install())
    return driver


def save_altair(fig, name, driver, path=FIG_PATH):
    """Saves an altair figure as png and html
    Args:
        fig: altair chart
        name: name to save the figure
        driver: webdriver
        path: path to save the figure
    """
    print(path)
    save(
        fig,
        f"{path}/png/{name}.png",
        method="selenium",
        webdriver=driver,
        scale_factor=5,
    )
    fig.save(f"{path}/html/{name}.html")


if __name__ == "__main__":
    altair_visualisation_setup()
