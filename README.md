vslearn
==================
**Author**: Vladimir Shteyn  
**GitHub**: [GitHub](https://github.com/mistervladimir)  
**LinkedIn**: [LinkedIn](https://www.linkedin.com/in/vladimir-shteyn/)  


Introduction
------------------
*vslearn* is an image annotation tool that helps non-technical folks generate ground truth bounding boxes used in training neural networks. Basically: (1) humans draw bounding boxes around objects of interest and (2) feed the images + bounding boxes into a neural net so it can learn to predict bounding boxes around similar objects. I created this product as part of my [Insight Data Science](https://www.insightdatascience.com/) project consulting for [WellthApp](https://wellthapp.com/home).


Installing & Running
------------------
Please clone from source by issuing the following shell commands:  
> git clone https://github.com/MisterVladimir/vslearn.git  
> cd vslearn  
> pip install .  

To run, navigate to the folder in which vslearn is installed, and enter the following shell command:  
> python main.py  


*vslearn* has only been tested on Ubuntu 18.04. However, *vslearn* is built with the multi-platform framework, Qt, so there's a good chance *vslearn* is also platform-independent. To help enable multi-platform support, please note your operating system when raising issues.


Test
------------------
After cloning the repo, run the following command from the root:  
> python setup.py test


User Guide
------------------
A comprehensive guide will be published soon, but until then, here's a preview of the app's main window. A black-to-white gradient image has been loaded and three bounding boxes have been drawn.    
![main_window](https://raw.githubusercontent.com/mistervladimir/vslearn/master/imgs/main_window.png)  


Requirements
------------------
pyside2  
tensorflow  
pillow  


License
------------------
GNUv3, see [LICENSE](https://github.com/MisterVladimir/vslearn/blob/master/LICENSE)
