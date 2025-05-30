# Quizzinator
This projects simulates the behavior of survey respondents using the DeepSeek (r1) LLM. 
The canonical location for this code repository is 

> https://github.com/randal-cox/quizzinator

# Setup
Make sure you have [python3.12](https://www.python.org/downloads/release/python-3120/) 
installed on your machine. Then, at the command line, cd into the project directory. 
Then run

> ./bin/setup

This will install all python libraries needed, ollama, and all the deepseek models 
you need for this project. Note that we install deepseek-r1 for the 1.5, 7, 32, and 70
billion parameter models. The 70B model requires a 64 GB machine to run, the 32 requires 
at least 32GB, so you may not be able to run all these models on your machine.

If all goes well, you should see something like this (though the subprocesses may
show some additional text)

You can also run this to make sure everythoing is working as planned

> ./bin/test

```
🚀 setup quizzinator
  🐍 python3.12 global upgrades
  🥚 virtual environment
  📦 requirements
  🤖 ollama
  🧠 deepseek models
🎉 setup complete.
```

# Data Sets
Quizzinator requires folders with some standard files in it. We include two example projects
used in the paper: consent and jealousy. These projects analyze some published data in the 
context of LLM answers. These projects are in the directory called data.

Take a look at data/consent for an example of the project directory. At minumum, it requires 
this structure. Over time, Quizzinator will create additional files and directories. Notably
html will appear in your project directory.

project_root/
--hints.csv
--questions.txt
--setup/
----human.txt
----answers.txt
----identity
----consent

## Hints
**hints.csv** is an ordinary csv file with columns corresponding to questions asked in
quizes or surveys. You may include additional meta-columns as well (e.g., respondant
ids, elapsed times, validation tests, etc). The rows are the answers given by humans 
in responding to this survey, encoded the way the questions are asked.

The responses are used for 'hints' given to the LLMs. For example, below we will show
how to tell an LLM that it has a gender, orientation, and bdsm role that coresponds
to the actual humans that took your survey (thereby allowing the LLM to mimick the 
demographics of your human respondants)

## Questions
**questions.txt** is a structured file that describes the questions of your survey. 
This is a more complicated file format and is described below. TL;DR, though, is that
there is a section for each question.

## Setup
**setup** is a folder of prompts given to the LLM to set up the context for the survey
and who you want the LLM to pretend to be. These prompts are just ordinary English
as you might sent to an LLM in an ordinary context to set it up to better respond
to your requests. In this case the prompts are designed to help the LLM role play 
as a lkinkster taking the survey we are administering.

### Setup/human
**setup/human.txt** is just a promprt exorting the LLM to role play as a human. In the 
example, it also specifies that the LLM will be an adult who is interested in consensual 
BDSM and kink.

### Setup/identity
**setup/identity.txt** is a prompt that is displayed to ask the LLMN to adopt a certain 
human identity based on it selecting randomly some persona according the categories 
asked (orientation, gender, bdsm role, etc). 

If Quizzinator is called with the --hints switch, this prompt is dropped in favor of
information gleaned from the human responses in the hints.csv file. In this case, each
instancve of the quiz will be prompted by a new row from hints.csv about the demographic
data in the hints.csv file.

### Setup/answers
**setup/answers.txt** is a prompt that asks the LLM to answer the survey questions in
a particular style, like "Answer: 3". This makes it easier to get answers that this code
base can efffectively parse.

### Setup/consent
**setup/consent** is a prompt that informs the LLM about the consent policies about
administering this survey. This also includes details about who is administering the
survey, reputation, and policies. This consent document is basically the one given
to humans except it includes a little context so the LLM knows the survey is from
a trusted source.

## html
This directory is produced by QUizzinator and includes the results from LLM responses
and statistical analyses. If you open it, you will find an index.html file. Open this
in your browser to look at results.

----

# Usage
Quizzinator has a number of command-line tools.

## setup
Described above. This sets up the local virtual environment and the LLM models.

## test
Described above. This runs the unit tests for the project. You can say --help to get
help with this command.

## experiment
You can get details about how to use this command by typing

>./bin/experiment --help

```
usage: experiment [-h] [--experiment EXPERIMENT] [--hints HINTS] [--questions QUESTIONS] 
                  [--timeout TIMEOUT] [--n N] [--attempts ATTEMPTS] [-m MODEL]
                  [--from-hints] [--skip-identity] [--skip-setup] [-v] [-r] [--use-cache]
                  dir

Run LLM-based survey simulations

positional arguments:
  dir                   Path to survey directory

options:
  -h, --help            show this help message and exit
  --experiment EXPERIMENT
                        The name of the experiment to generate
  --hints HINTS         Add the names of questions that the LLM should know the answers to ahead of time, separated by commas
  --questions QUESTIONS
                        Add the names of questions that are asked, separated by commas [def = all questions]
  --timeout TIMEOUT     Seconds before we timeout responses from the LLM
  --n N                 Number of respondents. 0 for match to hints.csv
  --attempts ATTEMPTS   How many times we will ask the question before giving up
  -m MODEL, --model MODEL
                        Ollama model name to use, like deepseek-r1:1.5b
  --from-hints          If set, just create data from the hints file, not from LLM queries
  --skip-identity       If set, do not inform the LLM about identity questions
  --skip-setup          If set, do not show inform the LLM about the context of the survey
  -v, --verbose         Show dialog as it happens
  -r, --reset           If set, recompute
  --use-cache           If set, load from cache instead of querying the LLM
```

For example, the following command will run a new experiment on the data in data/consent.

```
./bin/experiment \
  --hints Roles \
  --verbose  \
  --experiment Roles \
  --model deepseek-r1:1.5B \
  --n 66 \
  --questions PuPSafeword,RRSafeword,Roles \
  data/consent
```

This command will send 66 surveys to the 1.5 billion parameter Deep Seek model and collect the 
results. For this data set Role refers to BDSM roles, like Top, Bottom, Dom, Sub, etc.

Those 66 surveys will be constructed in very specific ways. Quizzinator will
- Tell the LLM that it is human and that it should answer questions succinctly
- get the answer about Role from hints.csv
- Tell the LLM that in the past it answered questions about its role in the way 
we fetched from hints
- Then ask the LLM the PuPSafeword and RRSafeword questions as specified in the 
questions.txt file
- Finally ask the Roles question (from the questions.txt file) to see if the LLM 
really internalized what we told it

Quizzinator will cache all these results as it gets them. So, if you have to interupt 
the run in the middle, Quizzinator will pick back up where it left off. When Quizzinator
finishes its run, it will produce html that lets you see the results of all the 
experiments you have run on this project (see below).

### Compuational Resources
Our paper describing Quizzinator used four Deep Seek models, with 1.5, 7, 32, and 70 billion 
parameters, respectively. The largest of these had substantial footprints

- 70B: 42 GB
- 32G: 19 GB
- 7B: 4.7 GB
- 1.5B: 1.1 GB

These models need to be in memory for use, so you should restrict the use of models to those
that can run on your machine. In addition to adequate memory, your machine will also need 
substantial GPU power.

For our paper, we used an M1 Max Macbook Pro with 64 GB of memory, a modestly powerful machine
for the time of the writing (2025). With this machine, full runs of the experiments described
inb bin/run (see below) took about a week of computation.

## paper
This bash script runs all the experiments described in our paper on Quizzinator. Details
are available in the linked paper, but in general, we looked at two published data sets.

Buss [citation needed]
Tarleton [citation needed]

The run bash command should give you some good hints about how to run bin/experiments on
your own data sets.