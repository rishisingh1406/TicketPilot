# Architecture Notes  Day 2 

## Major responsibilities 


### It shoud able to detect the jailbreak or harm attemp 

it detect the person doing the harm like he is trying to do jail attack or something and handels it correctly 

it exsit for security reason 

it needs to know the the user query and it shoud exesit between the user and the agent

protecting the agent from the user 

if the query is identifyed as jailbreak or harm the user should be blocked and the query should be passed to support team 

like it pass its decision and another component ship it to the team 

like it should retrun the user is blocked why it think so and return the entire chat and cause for its decison to support team 

it should acces it 

do nothing when its all safe 

security explicitly returns an allow decision -> agent continues


### it should be able to identify when the query is able to be handeled by the agent and when it needs to be passed to the support team 



like its main job is to identify weather the query can be answerd by looking into manual document like it is procedural type query if yes than it should execute it else it should pass it to the support team 

like if to generate the answer there is sufficient knwoledge  in manuel is present than it should answer by self or else pass it t

it should happen at the start of conversation and when the agent is not able to answer the user 

yes cuz this same responsiblity can be converted into one entire component 

like based on the query we will decide the manual contains sufficient knowledge 

like retrieval is another component it can be accesed by agent at any stage 

like agent retrieves relevent info if he thinks he can aswer it returns it else it passes to the support team 


"Given the query + current evidence,
can the agent safely answer this right now?"



