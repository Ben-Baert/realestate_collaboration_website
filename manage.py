from manager import Manager
from realestate.models import (Realestate,
                           UserRealestateReview)

manager = Manager()

@manager.arg('property_id', help='The id of the property you want all reviews to be removed for')
@manager.command
def remove_user_reviews_for_property(property_id):
    """
    Remove all property reviews associated
    with a certain property. Useful in case 
    a bug caused multiple reviews per user.
    """
    property_reviews_delete_query = (UserRealestateReview
                                     .delete()
                                     .where(UserRealestateReview.realestate ==
                                            property_id))
    property_reviews_delete_query.execute()
    print("Property reviews for property {} deleted!".format(property_id))

if __name__ == '__main__':
    manager.main()
