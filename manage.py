from manager import Manager
from houses.models import (Realestate,
                           UserRealestateReview)

manager = Manager()


@manager.command
def remove_user_reviews_for_property(property_id):
    property_reviews_delete_query = (UserRealestateReview
                                     .delete()
                                     .where(UserRealestateReview.realestate ==
                                            property_id))
    property_reviews_delete_query.execute()
    print("Property reviews for property {} deleted!".format(property_id))

if __name__ == '__main__':
    manager.main()
