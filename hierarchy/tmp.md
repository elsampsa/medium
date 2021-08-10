 
# Appendum

["Model-View-Controller"](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller) (MVC)

MVC is actually an old term that is not that well-defined nowadays.  Consider the traditional definition of the controller: "Accepts input and converts it to commands for the model or view".  You should read that as: "accepts static html form input and converts them to SQL commands".

Let's now take a modern JS frameworks which has components that intermediate continuously/reactively between the view and the model.  These components are called the ["ViewModels"](https://012.vuejs.org/guide/#Concepts_Overview) and the old MVC concept now becomes the "Model-ViewModel-Model" (MVMM) model.

Modern frontends/views can be very "reactive" by their own terms: think of an interactive input form that has some rules to check if the input fields are OK and which 
shows interactive warning messages in the GUI if there is an error in input.  Note also that in modern JS frameworks (such as Vue), both the view and the model are in the frontend JS code (and the backend is merely a data source).
