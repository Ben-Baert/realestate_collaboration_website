Feature:
    I want a list of houses, ordered by likeability
    Background:
        Given the website is set up correctly 
        And I am logged in
        And an intial test house is set up
    Scenario: Inputting a new house
        When I am on the homepage
        Then I will see the list of houses
