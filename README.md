# Monolingual Text Checker

Expand the text checker on macht.sprache by adding a monolingual text checking tool to highlight sensitive terms and provide alternatives and additional information within the same language.

## Isntallation & Usage

You can either access our monolingual text checker via this link: http://vm455.rz.uni-osnabrueck.de/user031/textchecker.wsgi/
(the only requirement for this is that you need to be in the Wifi of the university of Osnabrück, you can also use a VPN)

To set up the Monolingual Text Checker on your local machine, follow these steps:
1. Clone the project repository to your local machine and navigate to the project directory.
2. Ensure that Python is installed on your system, then install the required Python packages listed in requirements.txt by running 'pip install -r requirements.txt'

Accessing the Monolingual text checker from your local machine:
1. Run the textchecker.py script.
2. Access the application through a web browser by navigating to the appropriate URL.

Using the Monolingual text checker: 
1. Enter the text you want to check into the provided input field.
2. Select the desired language for checking, or choose the auto-detect option.
3. Click the "Check" button to initiate the text checking process.
4. View the results: Sensitive terms will be highlighted. Hover over these terms to see their descriptions and alternative suggestions.
5. Rate the alternative terms based on how good of an alternative they are for the original term on a scale from 1-5.
6. If a term is offensive, you can mark it accordingly. Multiple offensive markings will result in the highlight changing color, indicating the severity of the offense.

## Important decisions made during the project implementation
- Rating of alternative terms: We decided to deviate from the way ratings are handled on the macht.sprache website, trying to implement a more intuitive rating - a number between 1-5 - which the user can see directly next to the altrnative terms suggested, when hovering over the highlighted senstitive terms.
- Rating a term as offensive: We decided to add a possibility of rating a term as offensive, to provide users with a way to flag terms that they find offensive or inappropriate. In our implementation we coded hard boundaries (>3 changes highlight to light red, >4 changes hightlight to red). If this feature would be integrated into the macht.sprache website, the highlight boundaries should be calculated with ratios, based on how many users the website has.
- Which terms are detected in which language? We decided to detect both English and German terms within English text, as well as both English and German terms within German text. This approach increases the likelihood of detecting all sensitive terms, considering the prevalent use of English words in the German language.



This is where we planned our project, handled & distributed ToDos: https://github.com/users/Cl4ryty/projects/7/views/2
