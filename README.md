# FC Barcelona Match Report

This project provides a web application for analyzing and visualizing FC Barcelona's match data. The application is built with Streamlit, scrapes match data from WhoScored, processes and stores it in MongoDB, and displays it in a streamlined dashboard.

## Features

- **Data Scraping**: Scrapes FC Barcelona's match data from WhoScored.
- **MongoDB Storage**: Stores all match, team, player, and event data in MongoDB.
- **Data Visualization**: Interactive visualizations including pass networks, shot maps, match momentum, and team statistics.
- **Streamlit Interface**: Simple and interactive web dashboard for viewing and analyzing match data.

## Prerequisites

- Python 3.7+
- MongoDB instance
- Chrome WebDriver (for Selenium)

## Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/yusufwa7ied/FC-Barcelona-Match-Reports.git
    cd fc-barcelona-dashboard
    ```

2. **Set up environment variables**:
    - Create a `.env` file in the project root and add your MongoDB URI:
      ```plaintext
      MONGO_URI="your_mongodb_connection_string"
      ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. **Data Scraping**:
    - To scrape data and add it to your MongoDB, run:
      ```bash
      python scraper.py
      ```
    - This script only scrapes new matches not already in the database.

2. **Start the Streamlit App**:
    - To launch the dashboard, run:
      ```bash
      streamlit run dashboard.py
      ```
    - Access the dashboard at `http://localhost:8501`.

## Project Structure

- `scraper.py`: Web scraping script that fetches match data from WhoScored.
- `data_loader.py`: Loads data from MongoDB into DataFrames.
- `dashboard.py`: Streamlit app for displaying match data.
- `visualizations.py`: Contains functions for visualizations used in the app.
- `config.toml`: Configuration for Streamlit app styling.
- `.env`: Environment variables.

## Requirements

List of libraries in `requirements.txt`:
- `pandas`
- `numpy`
- `selenium`
- `pymongo`
- `beautifulsoup4`
- `streamlit`
- `mplsoccer`
- `matplotlib`
- `python-dotenv`

## Notes

- **Environment Variables**: Ensure `.env` is added to `.gitignore` to keep credentials secure.
- **Chrome WebDriver**: Ensure compatibility with your Chrome version. You may need to update the `webdriver.Chrome()` configuration in `scraper.py` based on your setup.
