Feature: As the website owner, I want all pages of the site protected
    Background: 
        Given the website is set up correctly 
        And the test account has been initiated

    Scenario: Not logged in visit to homepage
        Given I am not logged in
        When I am on the homepage
        Then I will see a login form
        And I will not see links to houses
        And I will not see links to appointments

    Scenario: Not logged in trying to visit prohibited pages
        Given I am not logged in
        When I attempt to view the houses page
        Then I will be redirected to the login page
        And I will see an alert that the previous page was prohibited

    Scenario: User logging in
        Given I am not logged in
        When I login
        Then I will be redirected to the houses page
        And I will see an alert that I logged in successfully
        And I will see links to houses
        And I will see links to appointments
        And I will see a link to post a new house

