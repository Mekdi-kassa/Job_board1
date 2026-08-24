from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Category, Job, Product, ProductInquiry
from .serializers import (
    CategorySerializer,
    JobPublicListSerializer,
    JobDetailSerializer,
    JobCreateUpdateSerializer,
    ProductSerializer,
    ProductInquirySerializer,
)
from .permissions import IsCompany, IsVerifiedCompany, IsJobOwner
from .filters import filter_jobs
from user.permissions import IsSuperAdmin


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


# ============================================================
# PUBLIC ENDPOINTS
# ============================================================

class JobPublicListView(generics.ListAPIView):
    """
    Public Job Browsing with Search, Filters, and Pagination.
    Returns only PUBLISHED jobs that have not passed their deadline.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = JobPublicListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Job.objects.filter(
            status=Job.Status.PUBLISHED
        ).select_related('company', 'category')
        
        # Apply filters & search helper
        return filter_jobs(queryset, self.request.query_params)


class JobPublicDetailView(APIView):
    """
    Retrieve single published job by UUID or Slug.
    Automatically increments views_count.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug_or_id):
        # Look up by UUID or Slug
        job = None
        if len(slug_or_id) == 36 and '-' in slug_or_id:
            try:
                job = Job.objects.select_related('company', 'category').get(id=slug_or_id)
            except Job.DoesNotExist:
                job = None

        if not job:
            job = get_object_or_404(
                Job.objects.select_related('company', 'category'),
                slug=slug_or_id
            )

        # Increment view count if viewed by public
        job.increment_views()

        serializer = JobDetailSerializer(job)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class CategoryListView(generics.ListAPIView):
    """
    List all active categories annotated with the count of active published jobs.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        today = timezone.now().date()
        return Category.objects.filter(is_active=True).annotate(
            job_count=Count(
                'jobs',
                filter=Q(
                    jobs__status=Job.Status.PUBLISHED
                ) & (Q(jobs__deadline__isnull=True) | Q(jobs__deadline__gte=today))
            )
        ).order_by('name')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class FeaturedJobsListView(generics.ListAPIView):
    """
    List top featured active published jobs.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = JobPublicListSerializer

    def get_queryset(self):
        today = timezone.now().date()
        return Job.objects.filter(
            status=Job.Status.PUBLISHED,
            is_featured=True
        ).filter(
            Q(deadline__isnull=True) | Q(deadline__gte=today)
        ).select_related('company', 'category').order_by('-created_at')[:8]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


# ============================================================
# COMPANY JOB MANAGEMENT (CRUD & STATUS)
# ============================================================

class CompanyJobCreateView(generics.CreateAPIView):
    """
    Create a new job posting (Draft or Published).
    Requires authenticated verified company account.
    """
    permission_classes = [permissions.IsAuthenticated, IsVerifiedCompany]
    serializer_class = JobCreateUpdateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            job = serializer.save()
            return Response({
                'success': True,
                'message': 'Job posting created successfully.',
                'data': JobDetailSerializer(job).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CompanyMyJobsListView(generics.ListAPIView):
    """
    List all jobs posted by the authenticated company.
    Includes drafts, active, and closed postings.
    """
    permission_classes = [permissions.IsAuthenticated, IsCompany]
    serializer_class = JobPublicListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Job.objects.filter(company=self.request.user).select_related('category')
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by('-created_at')


class CompanyJobDetailManageView(APIView):
    """
    Retrieve, Update, or Delete a job posting owned by the authenticated company.
    """
    permission_classes = [permissions.IsAuthenticated, IsJobOwner]

    def get_object(self, pk):
        job = get_object_or_404(Job.objects.select_related('category', 'company'), pk=pk)
        self.check_object_permissions(self.request, job)
        return job

    def get(self, request, pk):
        job = self.get_object(pk)
        serializer = JobDetailSerializer(job)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def patch(self, request, pk):
        job = self.get_object(pk)
        serializer = JobCreateUpdateSerializer(job, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            updated_job = serializer.save()
            return Response({
                'success': True,
                'message': 'Job posting updated successfully.',
                'data': JobDetailSerializer(updated_job).data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        job = self.get_object(pk)
        job.delete()
        return Response({
            'success': True,
            'message': 'Job posting deleted successfully.'
        }, status=status.HTTP_200_OK)


class CompanyJobToggleStatusView(APIView):
    """
    Toggle job status between PUBLISHED and CLOSED.
    """
    permission_classes = [permissions.IsAuthenticated, IsJobOwner]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        self.check_object_permissions(request, job)

        if job.status == Job.Status.PUBLISHED:
            job.status = Job.Status.CLOSED
        else:
            job.status = Job.Status.PUBLISHED
        
        job.save(update_fields=['status', 'updated_at'])

        return Response({
            'success': True,
            'message': f'Job status updated to {job.status}.',
            'data': {
                'id': str(job.id),
                'status': job.status,
                'is_active': job.is_active
            }
        }, status=status.HTTP_200_OK)


# ============================================================
# SUPER ADMIN JOB MODERATION
# ============================================================

class AdminJobListView(generics.ListAPIView):
    """
    List all platform jobs with filtering & pagination for Super Admins.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = JobPublicListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Job.objects.all().select_related('company', 'category')
        return filter_jobs(queryset, self.request.query_params)


class AdminJobToggleFeatureView(APIView):
    """
    Toggle is_featured flag for a job posting.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def patch(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        job.is_featured = not job.is_featured
        job.save(update_fields=['is_featured', 'updated_at'])
        return Response({
            'success': True,
            'message': f"Job {'featured' if job.is_featured else 'unfeatured'} successfully.",
            'data': {
                'id': str(job.id),
                'is_featured': job.is_featured
            }
        })


class AdminCategoryManageView(APIView):
    """
    Create, Update, or Deactivate Job Categories (Super Admin).
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response({
                'success': True,
                'message': 'Category created successfully.',
                'data': CategorySerializer(category).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response({
                'success': True,
                'message': 'Category updated successfully.',
                'data': CategorySerializer(updated).data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        return Response({
            'success': True,
            'message': 'Category deleted successfully.'
        }, status=status.HTTP_200_OK)


class AdminJobDetailManageView(APIView):
    """
    Super Admin manage / remove any job posting on the platform.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def delete(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        job.delete()
        return Response({
            'success': True,
            'message': 'Job posting removed by administrator.'
        }, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        status_val = request.data.get('status')
        if status_val:
            job.status = status_val
            job.save(update_fields=['status', 'updated_at'])
            return Response({
                'success': True,
                'message': f"Job status updated to {job.status}.",
                'data': {'id': str(job.id), 'status': job.status}
            })
        return Response({'success': False, 'message': 'No status provided.'}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# ECOMMERCE PRODUCT MARKETPLACE VIEWS
# ============================================================

class ProductListCreateView(APIView):
    """
    List active products or post a new product listing.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get(self, request):
        queryset = Product.objects.select_related('seller').filter(status=Product.Status.ACTIVE)

        q = request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(short_description__icontains=q) |
                Q(category__icontains=q)
            )

        category = request.query_params.get('category')
        if category and category != 'all':
            queryset = queryset.filter(category__iexact=category)

        min_price = request.query_params.get('min_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass

        max_price = request.query_params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass

        sort = request.query_params.get('sort', '-created_at')
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'popular':
            queryset = queryset.order_by('-views_count', '-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            product = serializer.save()
            return Response({
                'success': True,
                'message': 'Product listed successfully.',
                'data': ProductSerializer(product, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailManageView(APIView):
    """
    Retrieve, update or delete a product listing.
    """
    def get_permissions(self):
        if self.request.method in ['PATCH', 'PUT', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_object(self, slug_or_id):
        try:
            return Product.objects.select_related('seller').get(pk=slug_or_id)
        except (Product.DoesNotExist, ValueError):
            return get_object_or_404(Product.objects.select_related('seller'), slug=slug_or_id)

    def get(self, request, slug_or_id):
        product = self.get_object(slug_or_id)
        # Increment views atomically
        Product.objects.filter(pk=product.pk).update(views_count=Product.objects.filter(pk=product.pk).values_list('views_count', flat=True)[0] + 1)
        product.refresh_from_db(fields=['views_count'])
        serializer = ProductSerializer(product, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        })

    def patch(self, request, slug_or_id):
        product = self.get_object(slug_or_id)
        # Check permissions: only seller or admin
        if product.seller != request.user and not (request.user.is_superuser or getattr(request.user, 'role', '') == 'admin'):
            return Response({'success': False, 'message': 'You do not have permission to edit this product.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProductSerializer(product, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Product updated successfully.',
                'data': serializer.data
            })
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug_or_id):
        product = self.get_object(slug_or_id)
        if product.seller != request.user and not (request.user.is_superuser or getattr(request.user, 'role', '') == 'admin'):
            return Response({'success': False, 'message': 'You do not have permission to delete this product.'}, status=status.HTTP_403_FORBIDDEN)

        product.delete()
        return Response({
            'success': True,
            'message': 'Product removed from marketplace.'
        }, status=status.HTTP_200_OK)


class ProductInquiryCreateView(APIView):
    """
    Send buyer inquiry to product seller.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, slug_or_id):
        try:
            product = Product.objects.get(pk=slug_or_id)
        except (Product.DoesNotExist, ValueError):
            product = get_object_or_404(Product, slug=slug_or_id)

        data = request.data.copy()
        data['product'] = product.id
        serializer = ProductInquirySerializer(data=data)
        if serializer.is_valid():
            inquiry = serializer.save(sender=request.user if request.user.is_authenticated else None)
            return Response({
                'success': True,
                'message': 'Your inquiry has been sent to the seller.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class MyProductsListView(APIView):
    """
    List authenticated user's own listed products.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        products = Product.objects.filter(seller=request.user).order_by('-created_at')
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': products.count(),
            'data': serializer.data
        })
