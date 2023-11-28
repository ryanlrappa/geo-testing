import tempfile
import rpy2.robjects as robjects
from rpy2.robjects.packages import importr
from rpy2.robjects.conversion import localconverter

from io import BytesIO
from PIL import Image


def make_geoplot(r, plot_R_code, inline=True):
    '''
    Shows plots from Meta GeoLift functions either inline or in a .png file
    Meta GeoLift docs: https://facebookincubator.github.io/GeoLift/

    Args:
        r (R instance obj): R instance from r = robjects.r
        plot_R_code (str): R code snippet from GeoLift used for plotting. Example:
                           "GeoPlot(GeoTestData_PreTest,
                                    Y_id = 'Y',
                                    time_id = 'time',
                                    location_id = 'location')"
        inline (bool): Default True shows plots inline in ipython notebooks.
                       Set to False to output .png files

    Returns:
        R plot specified in first arg
    '''

    with localconverter(robjects.default_converter):
        
        # Import R's base package
        base = importr('base')

        # Define the R function to create and capture the plot        
        r('''
        create_plot <- function() {

          # Create the plot
          p <- ''' + plot_R_code + '''

          # Open a png device in memory
          grDevices::png(tempfile(), bg = "transparent")
          print(p)
          grDevices::dev.off()

          # Read the file and return its content
          temp_file <- tempfile()
          grDevices::png(temp_file, width=800, height=600, pointsize=16, bg="transparent")
          print(p)
          grDevices::dev.off()

          raw_vector <- base::readBin(temp_file, what = "raw", n = file.info(temp_file)$size)
          unlink(temp_file) # Remove the temp file
          return(raw_vector)
        }
        ''')

        # Call the R function
        raw_vector = robjects.r['create_plot']()
        
        # Convert the R raw vector to Python bytes
        img_data = bytes(raw_vector)

        # Use BytesIO to handle the image data
        img_buffer = BytesIO(img_data)

        # Open the image using PIL
        img = Image.open(img_buffer)

        # Display the image 
        if inline == True:
            display(img)  # display image inline in jupyter/ipython
        else:
            img.show()  # img.show() outputs a .png popup that can be saved


def make_market_plot(r, market_id, inline=True):
    '''
    Shows power analysis diagnostic plots from Meta GeoLift, either inline or in a .png file
    Meta GeoLift docs: https://facebookincubator.github.io/GeoLift/

    Args:
        r (R instance obj): R instance from r = robjects.r
        market_id (int): number from MarketSelections table ID col, denoting treatment group markets
        inline (bool): Default True shows plots inline in ipython notebooks.
                       Set to False to output .png files

    Returns:
        R plot for power analysis diagnostic
    '''

    with localconverter(robjects.default_converter):
        
        # Create a temporary file to save the plot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            tmpfile_name = tmpfile.name

        # Run the R plotting command and save the plot to the temporary file
        r(f'''
        png(filename="{tmpfile_name}", width=800, height=600, pointsize=16)
        plot(MarketSelections, market_ID = {market_id}, print_summary = TRUE)
        dev.off()
        ''')

        # Open the saved image using Pillow and return the image object
        img = Image.open(tmpfile_name)
        
        # Display the image
        if inline == True:
            display(img)
        else:
            img.show()


def make_market_deep_dive_plot(r, market_id, lookback_window, inline=True):
    '''
    Shows power analysis curves from Meta GeoLift, either inline or in a .png file, per:
    facebookincubator.github.io/GeoLift/docs/GettingStarted/Walkthrough#power-output---deep-dive-into-power-curves
    
    In order to ensure that power is consistent throughout time for these locations,
    we can run more than 1 simulation for each of the top contenders that came out of
    GeoLiftMarketSelection, using this function.
    
    NOTE: You could repeat this process for the top 5 treatment combinations that come out of
    GeoLiftMarketSelection, with increased lookback windows and compare their power curves.

    Args:
        r (R instance obj): R instance from r = robjects.r
        market_id (int): number from MarketSelections table ID col, denoting treatment group markets
        lookback_window (int): number of periods for lookback window for diagnostic
        inline (bool): Default True shows plots inline in ipython notebooks.
                       Set to False to output .png files

    Returns:
        R plot for power analysis diagnostic
    '''

    # R code to create diagnostic table power_data
    r(f'''
        market_id = {market_id}
        market_row <- MarketSelections$BestMarkets %>% dplyr::filter(ID == market_id)
        treatment_locations <- stringr::str_split(market_row$location, ", ")[[1]]
        treatment_duration <- market_row$duration
        lookback_window <- {lookback_window}

        power_data <- GeoLiftPower(
          data = GeoTestData_PreTest,
          locations = treatment_locations,
          effect_size = seq(-0.25, 0.25, 0.01),
          lookback_window = lookback_window,
          treatment_periods = treatment_duration,
          cpic = 7.5,
          side_of_test = "two_sided"
          )
    ''')

    # R code for plot
    p = '''plot(power_data, show_mde = TRUE, smoothed_values = FALSE, breaks_x_axis = 5) +
                ggplot2::labs(caption = unique(power_data$location))'''

    # invoking make_geoplot as a workaround for bug documented here:
    # github.com/tidyverse/ggplot2/issues/2514
    make_geoplot(r, p)


def make_market_plot_multicell(r, market_ids, inline=True):
    '''
    Shows power analysis diagnostic plots from Meta GeoLift, either inline or in a .png file
    Meta GeoLift docs: https://facebookincubator.github.io/GeoLift/

    Args:
        r (R instance obj): R instance from r = robjects.r
        market_ids (list of ints): numbers from Markets table ID col, denoting treatment group markets
        inline (bool): Default True shows plots inline in ipython notebooks.
                       Set to False to output .png files

    Returns:
        R plot for power analysis diagnostic
    '''

    with localconverter(robjects.default_converter):
        
        # Cells and Market IDs in an R list
        market_locs = ", ".join("cell_{} = {}".format(i+1, n) for i, n in enumerate(market_ids))
        r(f'''
        test_locs <- list({market_locs})
        ''')

        # Create a temporary file to save the plot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            tmpfile_name = tmpfile.name

        # Run the R plotting command and save the plot to the temporary file
        r(f'''
        png(filename="{tmpfile_name}", width=800, height=600, pointsize=16)
        plot(Markets, test_markets = test_locs, type = "Lift", stacked = TRUE)
        dev.off()
        ''')

        # Open the saved image using Pillow and return the image object
        img = Image.open(tmpfile_name)
        
        # Display the image
        if inline == True:
            display(img)
        else:
            img.show()


def make_market_deep_dive_plot_multicell(r, market_ids, lookback_window, inline=True):
    '''
    Shows power analysis curves from Meta GeoLift, either inline or in a .png file, per:
    facebookincubator.github.io/GeoLift/docs/GettingStarted/Walkthrough#power-output---deep-dive-into-power-curves

    In order to ensure that power is consistent throughout time for these locations,
    we can run more than 1 simulation for each of the top contenders that came out of
    GeoLiftMarketSelection, using this function.

    NOTE: You could repeat this process for the top 5 treatment combinations that come out of
    GeoLiftMarketSelection, with increased lookback windows and compare their power curves.

    Args:
        r (R instance obj): R instance from r = robjects.r
        market_ids (list of ints): numbers from Markets table ID col, denoting treatment group markets
        lookback_window (int): number of periods for lookback window for diagnostic
        inline (bool): Default True shows plots inline in ipython notebooks.
                       Set to False to output .png files

    Returns:
        R plot for power analysis diagnostic
    '''

    # Cells and Market IDs in an R list
    market_locs = ", ".join("cell_{} = {}".format(i+1, n) for i, n in enumerate(market_ids))
    r(f'''
    test_locs <- list({market_locs})
    ''')

    # R code to create diagnostic table
    r(f'''
        Power <- MultiCellPower(Markets,
                                test_markets = test_locs,
                                effect_size =  seq(-0.5, 0.5, 0.05),
                                lookback_window = {lookback_window})
    ''')

    with localconverter(robjects.default_converter):
        # Create a temporary file to save the plot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            tmpfile_name = tmpfile.name

        # Run the R plotting command and save the plot to the temporary file
        r(f'''
        png(filename="{tmpfile_name}", width=800, height=600, pointsize=16)
        plot(Power, actual_values = TRUE, thed_values = FALSE, show_mde = TRUE, breaks_x_axis = 15, stacked = TRUE)
        dev.off()
        ''')

        # Open the saved image using Pillow and return the image object
        img = Image.open(tmpfile_name)

        # Display the image
        if inline == True:
            display(img)
        else:
            img.show()
