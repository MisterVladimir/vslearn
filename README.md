vslearn
==================
**Author**: Vladimir Shteyn  
**GitHub**: [GitHub](https://github.com/mistervladimir)  
**LinkedIn**: [LinkedIn](https://www.linkedin.com/in/vladimir-shteyn/)  


Introduction
------------------
*vslearn* is an image annotation tool that helps non-technical folks generate ground truth bounding boxes used in training neural networks. Basically: (1) humans draw bounding boxes around objects of interest and (2) feed the images + bounding boxes into a neural net so it can learn to predict bounding boxes around similar objects. I created this product as part of my [Insight Data Science](https://www.insightdatascience.com/) project consulting for [WellthApp](https://wellthapp.com/home).


Requirements
------------------
pyside2  
tensorflow  
pillow  


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

Here's how a user can perform a few key app functions:  
#### enter "image editing mode"
This allows the user to modify bounding boxes overlaid on the image, e.g. draw new bounding boxes, stretch bounding boxes, delete them, etc. To enter image editing mode, click the red X button or press the "2" hotkey.  
#### indicate the bounding boxes need no changes  
Click the green checkbox button or press the "1" hotkey. This forces the user to think twice before moving on to the next image by clicking the ENTER button (see **accept an image and its bounding boxes** bellow).
#### accept an image and its bounding boxes
This will register any changes to bounding boxes in the current view, or, if an image has been marked as "correctly labeled", internally notes that the image has been reviewed by a human with the entered UserID. To "accept" an image and its bounding boxes, press the ENTER button or the "enter" keyboard key. Note that this button is only enabled after the user marks an image as "correctly labeled" or while in "image editing mode".  
#### draw a bounding box
First, enter image editing mode (see **enter image editing mode** above) and click ADD RECTANGLE (or pressing the "3" keyboard key). Bounding boxes may be drawn with intuitive click and drag mouse actions.  
#### delete a bounding box
In "image editing mode" (see **enter image editing mode** above), left click on a bounding box to select it, and then press the "Del" key. Bounding boxes may also be selected with the mouse via click and drag, rubber band-type mouse interface.  
#### adjust (i.e. stretch) existing bounding boxes
While in "image editing mode" (see **enter image editing mode** above), select a bounding box by left clicking on it. With the mouse cursor hovering inside the selected bounding box, roll the mouse wheel close to the bounding box edge to be adjusted. Bounding box edges may be pushed outwards or pulled inwards. In the future, I hope to implement a more convenient click and drag interface.  
#### export images
To save image and bounding boxes together in Tensorflow Record format for model training, click the *File* menu item > *Export to...* > *Tensorflow Record*. Bounding boxes alone may be exported as JSON format by doing *Export to...* > *JSON*. The JSON files only store bounding box data (plus an image ID) such that the user may pause a bounding box labeling session. When the user re-opens the app, they can simply *File* > *Open Images...* to load images, and then load the associated bounding boxes stored as JSON. In its current implementation, bounding boxes and images are associated via the image file names. **Do not change the image filenames once they have been labeled.** It is OK to move the image to another folder or even change their format, e.g. JPEG -> PNG.


License
------------------
GNUv3, see [LICENSE](https://github.com/MisterVladimir/vslearn/blob/master/LICENSE)
