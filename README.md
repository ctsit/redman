# redman

Welcome to the REDmineMANager (**redman**) tool page.

This tool can save some of your time when doing repetitive actions such as
copying stories and tasks from one sprint to a new one.

The target user-base for the redman tool is anybody using
[redmine](http://www.redmine.org) in combination with the 
[redmine backlogs plugin](https://github.com/backlogs/redmine_backlogs).

# Setup

The redman tool is compatible with python 2.7 so please create a virtual
environment for python 2.7 if your computer setup uses python 3 by default.
For more instructions on how to use virtual environments please got to
[https://virtualenv.pypa.io/en/latest/](https://virtualenv.pypa.io/en/latest/).

<pre>
pip install virtualenv
</pre>

Create a virtual environmanet and activate it, then install the
python requirements:

<pre>
git clone git@github.com:ctsit/redman.git
cd redman
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
</pre>


# Usage

- Create one or more template sprints in Redmine using the web interface.

Note: In the next steps we will assume that you already created a sprint
called `TEMPLATE_SPRINT_GREEN` and we will use it to run our tool.

- Create the fabric.py file in which we configure the tool:

<pre>
cp sample.fabric.py production/fabric.py
</pre>

- Edit the production/fabric.py file lines which contain
information about redmine:

<pre>
api_url: https://your_redmine_url.com
api_key: some_long_string_you_can_get_from_my_account_page_under_api_access_key (see the screenshots section below)
sprint_name_green: 'TEMPLATE_SPRINT_GREEN'
</pre>

- Run the redman tool:

<pre>
fab production copy_sprint_template_green
or
make prod_green
</pre>

Note: If you receive an error like
<pre>
No need to copy the sprint since days passed [22] is not a multiple of [14]
specified in the `fabric.py` config file.
</pre>
then please update the `repeat_after` parameter in the `production/fabric.py`
config file to match the value `22`. The reason for this error is that
redman is configured to be run automatically every `X` days from a specific date
(in our case on day 14, 28, 42... and so on).


# Screenshots

Obtaining the Redmine API access key:

[![Usage](img/redmine_api_key.png)]()

An example of session using the redman tool:

[![Usage](img/usage.jpg)]()


# Contributors

The application was written by Andrei Sura with tremendous support and fedback
from the entire
[CTS-IT team](https://www.ctsi.ufl.edu/research/study-development/informatics-consulting/).
