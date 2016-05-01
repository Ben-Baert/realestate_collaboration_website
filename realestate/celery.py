from peewee import IntegrityError
from celery import Celery, Task
from realestate import app
from flask import has_request_context, request, make_response
from .models import (Realestate,
                     RealestateInformationCategory,
                     RealestateInformation,
                     RealestateCriterion,
                     RealestateCriterionScore,
                     Feature,
                     RealestateFeature,
                     User,
                     database)
from realestate.scrapers.realo import Realo, RealoSearch


celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


class RequestContextTask(Task):
    """Base class for tasks that originate from Flask request handlers
    and carry over most of the request context data.
    This has an advantage of being able to access all the usual information
    that the HTTP request has and use them within the task. Pontential
    use cases include e.g. formatting URLs for external use in emails sent
    by tasks.
    """

    abstract = True

    #: Name of the additional parameter passed to tasks
    #: that contains information about the original Flask request context.
    CONTEXT_ARG_NAME = '_flask_request_context'
    
    def __call__(self, *args, **kwargs):
        """Execute task code with given arguments."""
        call = lambda: super(RequestContextTask, self).__call__(*args, **kwargs)

        context = kwargs.pop(self.CONTEXT_ARG_NAME, None)
        if context is None or has_request_context():
            return call()

        with app.test_request_context(**context):
            result = call()

            # process a fake "Response" so that
            # ``@after_request`` hooks are executed
            app.process_response(make_response(result or ''))

        return result

    def apply_async(self, args=None, kwargs=None, **rest):
        if rest.pop('with_request_context', True):
            self._include_request_context(kwargs)
        return super(RequestContextTask, self).apply_async(args, kwargs, **rest)

    def apply(self, args=None, kwargs=None, **rest):
        if rest.pop('with_request_context', True):
            self._include_request_context(kwargs)
        return super(RequestContextTask, self).apply(args, kwargs, **rest)

    def retry(self, args=None, kwargs=None, **rest):
        if rest.pop('with_request_context', True):
            self._include_request_context(kwargs)
        return super(RequestContextTask, self).retry(args, kwargs, **rest)

    def _include_request_context(self, kwargs):
        """Includes all the information about current Flask request context
        as an additional argument to the task.
        """

        if not has_request_context():
            return

        # keys correspond to arguments of :meth:`Flask.test_request_context`
        context = {
            'path': request.path,
            'base_url': request.url_root,
            'method': request.method,
            'headers': dict(request.headers),
        }
        if '?' in request.url:
            context['query_string'] = request.url[(request.url.find('?') + 1):]

        kwargs[self.CONTEXT_ARG_NAME] = context

celery.Task = RequestContextTask


@celery.task
def generate_feed(*args, **kwargs):
    urls = [realestate.realo_url for realestate in Realestate.select()]
    with RealoSearch(*args, **kwargs) as search:
        for item in search.houses_urls():
            if item not in urls:
                add_realo_realestate.delay(item)
    prepare_caches.delay()


@celery.task
@database.atomic()
def prepare_caches():
    for user in User.select():
        cached_queue = sorted(Realestate.full_queue(user),
                              key=lambda x: (-x.score, -x._score))
        for i in range(len(user.cached_queue)):
            user.cached_queue.pop()
        #print(user.cached_queue)
        user.cached_queue.extend([x._id for x in cached_queue])


@celery.task
@database.atomic()
def add_realo_realestate(url):
    with Realo(url) as realo_realestate:
        print(url)
        lat, lng = realo_realestate.lat_lng()
        inhabitable_area, total_area = realo_realestate.area()
        try:
            realestate = Realestate.create(
                    added_on=realo_realestate.added_on(),
                    realestate_type=realo_realestate.realestate_type(),
                    seller=realo_realestate.seller(),
                    address=realo_realestate.address(),
                    inhabitable_area=inhabitable_area,
                    total_area=total_area,
                    lat=lat,
                    lng=lng,
                    description=realo_realestate.description(),
                    price=realo_realestate.price(),
                    realo_url=url,
                    thumbnail_pictures=realo_realestate.thumbnail_pictures(),
                    main_pictures=realo_realestate.main_pictures(),
                    )
            print(realestate.realo_url + " added.")
        except IntegrityError:
            return

        for information in realo_realestate.information():
            category, _ = (RealestateInformationCategory
                           .get_or_create(_realo_name=information[0]))

            RealestateInformation.create(
                realestate=realestate,
                category=category,
                value=information[1])

        for criterion in RealestateCriterion.select():
            RealestateCriterionScore.create(criterion=criterion,
                                            realestate=realestate)

        for feature in realo_realestate.features():
            feature, _ = Feature.get_or_create(name=feature)
            RealestateFeature.create(feature=feature, realestate=realestate)
    print("Ended!")
