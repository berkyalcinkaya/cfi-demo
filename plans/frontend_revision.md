## Front end workflows version 2

Status: envisioning stage with a scaffold of pre-existing work. The current verion in fron
Goal: convey the value of this application to an embryologist who wants human-in-the-loop tools to improve embryo selection and ultimately drive up embryology success rates

We have previously implemented a v0 of the frontend which begins to tackle the three highest value workflows in frontend_workflows.md. It is now time to revise. 

## Initial simple fixes and small features
1) fix: morphokinetic timeline does not show short-lived time stages (eg t3 is not on timeline)
2) fix: clicking an embryo should reset timepoint to 0
3) fix: modify layout to reduce wait space and improve readability. Thoroughly inspect frontend-v1.png to understand how to improve UI

## Structural changes
1. display some notion of a patient selector in a sidebar. Embryologists want to see that other patients will be selectable (even though dummy data includes one patient only). Make this implementation robust and compatible as database hydrates

2. less emphasis on prediction scores and more emphasis on top 3. our ploidy and live birth predictions do best on top 3 predictions based on eval data. It is also well known that neural networks scores are not always calibrated. 
- find some way to highlight the top 3 live birth predicted embryos and display the other beneath with less emphasises
- display only euploid or aneuploid with colored, filled indicator but no direct numeric indication

3. Add: normalized morphokinetic comparison page to see the timeline of all embryos stacked on the same page to enable embryologist comparison of morphokientic timelines

Suggest any other features as well based on your understanding of the project.

