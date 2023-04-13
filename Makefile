# Signifies our desired python version
# Makefile macros (or variables) are defined a little bit differently than traditional bash, keep in mind that in the Makefile there's top-level Makefile-only syntax, and everything else is bash script syntax.
PYTHON = python3

# .PHONY defines parts of the makefile that are not dependant on any specific file
# This is most often used to store functions
.PHONY = help prepare test run clean

# Defining an array variable
FILES = input output

APP_LOG_FOLDER="${HOME}/log/trading-backoffice"

# Defines the default target that `make` will to try to make, or in the case of a phony target, execute the specified commands
# This target is executed whenever we just type `make`
.DEFAULT_GOAL = help

# The @ makes sure that the command itself isn't echoed in the terminal
help:
	@echo "---------------HELP-----------------"
	@echo "To prepare the project type make prepare"
	@echo "To test the project type make test"
	@echo "To clean the project type make run"
	@echo "To run the project type make run"
	@echo "------------------------------------"

prepare:
	@echo "Prepaparing ..."
	${PYTHON} -m venv venv
	. venv/bin/activate && ${PYTHON} -m pip install -U pip wheel setuptools
	. venv/bin/activate && pip install -r requirements.txt
	mkdir -p ${APP_LOG_FOLDER}

test:
	@echo "Testing ..."
	. venv/bin/activate && ${PYTHON} -m unittest discover -v

run:
	@echo "Run ..."
	. venv/bin/activate && jupyter-lab

clean:
	@echo "Cleaning ..."
	rm -rf dist
	rm -rf jupyter_notebooks.egg-info
	rm -rf venv
	
position_portfolio_trades:
	libreoffice notebooks/placeTrades/bybitPositionPortfolio/data/trades.csv

swing_portfolio_trades:
	libreoffice notebooks/placeTrades/bybitSwingPortfolio/data/trades.csv 

intraday_portfolio_trades:
	libreoffice notebooks/placeTrades/bybitIntradayPortfolio/data/trades.csv 

tw_downloader_trades:
	libreoffice notebooks/utils/tradingViewImagesDownloader/data/trades.csv 
