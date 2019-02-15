vslearn
==================
**Author**: Vladimir Shteyn  
**GitHub**: [GitHub](https://github.com/mistervladimir)  
**LinkedIn**: [LinkedIn](https://www.linkedin.com/in/vladimir-shteyn/)  


Introduction
------------------
*vslearn* is an image annotation tool that helps non-technical folks generate ground truth bounding boxes used in training neural networks. Basically: (1) humans draw bounding boxes around objects of interest and (2) feed the images + bounding boxes into a neural net so it can learn to predict bounding boxes around similar objects. I created this product as part of my [Insight Data Science](https://www.insightdatascience.com/) project consulting for [WellthApp](https://wellthapp.com/home).


Installation
------------------
Only installation from source is available right now.


Test
------------------
After cloning the repo, run the following command from the root:  
> python setup.py test


Requirements
------------------
PyQt5  
tensorflow  
dataclasses


License
------------------
GNUv3, see [LICENSE](https://github.com/MisterVladimir/vslearn/blob/master/LICENSE)
