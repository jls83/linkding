from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from bookmarks import queries
from bookmarks.api.serializers import BookmarkSerializer, TagSerializer
from bookmarks.models import Bookmark, BookmarkFilters, Tag, User
from bookmarks.services.bookmarks import archive_bookmark, unarchive_bookmark, website_loader
from bookmarks.services.website_loader import WebsiteMetadata


class BookmarkViewSet(viewsets.GenericViewSet,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin):
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        user = self.request.user
        # For list action, use query set that applies search and tag projections
        if self.action == 'list':
            query_string = self.request.GET.get('q')
            return queries.query_bookmarks(user, user.profile, query_string)

        # For single entity actions use default query set without projections
        return Bookmark.objects.all().filter(owner=user)

    def get_serializer_context(self):
        return {'user': self.request.user}

    @action(methods=['get'], detail=False)
    def archived(self, request):
        user = request.user
        query_string = request.GET.get('q')
        query_set = queries.query_archived_bookmarks(user, user.profile, query_string)
        page = self.paginate_queryset(query_set)
        serializer = self.get_serializer_class()
        data = serializer(page, many=True).data
        return self.get_paginated_response(data)

    @action(methods=['get'], detail=False)
    def shared(self, request):
        filters = BookmarkFilters(request)
        user = User.objects.filter(username=filters.user).first()
        query_set = queries.query_shared_bookmarks(user, request.user.profile, filters.query)
        page = self.paginate_queryset(query_set)
        serializer = self.get_serializer_class()
        data = serializer(page, many=True).data
        return self.get_paginated_response(data)

    @action(methods=['post'], detail=True)
    def archive(self, request, pk):
        bookmark = self.get_object()
        archive_bookmark(bookmark)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=True)
    def unarchive(self, request, pk):
        bookmark = self.get_object()
        unarchive_bookmark(bookmark)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def check(self, request):
        url = request.GET.get('url')
        bookmark = Bookmark.objects.filter(owner=request.user, url=url).first()
        existing_bookmark_data = self.get_serializer(bookmark).data if bookmark else None

        # Either return metadata from existing bookmark, or scrape from URL
        if bookmark:
            metadata = WebsiteMetadata(url, bookmark.website_title, bookmark.website_description)
        else:
            metadata = website_loader.load_website_metadata(url)

        return Response({
            'bookmark': existing_bookmark_data,
            'metadata': metadata.to_dict()
        }, status=status.HTTP_200_OK)


class TagViewSet(viewsets.GenericViewSet,
                 mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.CreateModelMixin):
    serializer_class = TagSerializer

    def get_queryset(self):
        user = self.request.user
        return Tag.objects.all().filter(owner=user)

    def get_serializer_context(self):
        return {'user': self.request.user}


router = DefaultRouter()
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')
router.register(r'tags', TagViewSet, basename='tag')
