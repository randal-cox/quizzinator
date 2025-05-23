# Quizzinator
This projects simulates the behavior of survey respondents using the DeepSeek (r1) LLM.

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
Quizzinator requires folders with some standard files in it. The included directory, echo,
is an excellent example of project directory. At minumum, it requires this structure
root/
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

----

# Usage
Quizzinator has a number of command-line tools.

## setup
Described above. This sets up the local virtual environment and the LLM models.

## test
Described above. This runs the unit tests for the project.

## experiment

