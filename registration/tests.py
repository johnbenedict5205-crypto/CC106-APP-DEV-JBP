from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Student


class StudentDirectoryTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username='staff',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)
        self.student = Student.objects.create(
            student_id='TEST-001',
            first_name='Taylor',
            last_name='Example',
            gender='Female',
            date_of_birth='2000-01-01',
            contact_no='09123456789',
        )
        Student.objects.create(
            student_id='TEST-002',
            first_name='Alex',
            last_name='Sample',
            gender='Male',
            date_of_birth='2001-02-02',
            contact_no='09123456780',
        )

    def test_directory_lists_students_and_searches_each_supported_field(self):
        response = self.client.get(reverse('student_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST-001')
        self.assertContains(response, 'TEST-002')

        for query in ('test-001', 'taylor', 'example'):
            with self.subTest(query=query):
                response = self.client.get(reverse('student_list'), {'q': query})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'TEST-001')
                self.assertNotContains(response, 'TEST-002')

    def test_detail_and_update_workflow(self):
        detail_url = reverse('student_detail', args=[self.student.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '09123456789')
        self.assertContains(response, 'registration/style.css')

        response = self.client.post(
            reverse('student_update', args=[self.student.pk]),
            {
                'student_id': 'TEST-001',
                'first_name': 'Jordan',
                'last_name': 'Example',
                'gender': 'Female',
                'date_of_birth': '2000-01-01',
                'contact_no': '09123456789',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student record updated successfully.')
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Jordan')

    def test_create_and_invalid_form_workflow(self):
        form_response = self.client.get(reverse('student_create'))
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, 'registration/style.css')

        response = self.client.post(
            reverse('student_create'),
            {
                'student_id': 'TEST-003',
                'first_name': 'Jamie',
                'last_name': 'Reyes',
                'gender': 'Female',
                'date_of_birth': '2002-03-04',
                'contact_no': '09123456781',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student record created successfully.')
        self.assertTrue(Student.objects.filter(student_id='TEST-003').exists())

        response = self.client.post(
            reverse('student_create'),
            {
                'student_id': 'TEST-004',
                'first_name': 'Casey',
                'last_name': 'Missing',
                'gender': 'Male',
                'date_of_birth': '2002-03-04',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertFalse(Student.objects.filter(student_id='TEST-004').exists())

    def test_delete_requires_confirmation_and_post(self):
        delete_url = reverse('student_delete', args=[self.student.pk])
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Student Deletion')
        self.assertContains(response, 'registration/style.css')
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())

        response = self.client.post(delete_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student record deleted successfully.')
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())

    def test_delete_post_requires_csrf_token(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(get_user_model().objects.get(username='staff'))
        delete_url = reverse('student_delete', args=[self.student.pk])
        response = client.post(delete_url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())


class StudentRegistrationTests(TestCase):
    def test_existing_landing_and_home_pages_still_load(self):
        landing_response = self.client.get(reverse('landing'))
        self.assertEqual(landing_response.status_code, 200)
        self.assertContains(landing_response, 'Welcome to My Django Application')

        home_response = self.client.get(reverse('home'))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'Welcome to my first Django application!')

    def test_registration_form_loads(self):
        response = self.client.get(reverse('student_registration'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('student_list'))
        for field in (
            'student_id',
            'first_name',
            'last_name',
            'gender',
            'date_of_birth',
            'contact_no',
        ):
            self.assertContains(response, f'name="{field}"')
        self.assertContains(response, 'Register Student')

    def test_uppercase_registration_url_redirects_to_canonical_url(self):
        response = self.client.get('/Registration/')

        self.assertRedirects(response, reverse('student_registration'))

    def test_student_registration_aliases_redirect_to_canonical_url(self):
        for url in ('/student/registration', '/student/registration/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, reverse('student_registration'))

    def test_valid_registration_creates_student_and_shows_success(self):
        response = self.client.post(
            reverse('student_registration'),
            {
                'student_id': 'TEST-001',
                'first_name': 'Taylor',
                'last_name': 'Example',
                'gender': 'Female',
                'date_of_birth': '2000-01-01',
                'contact_no': '09123456789',
            },
        )

        self.assertRedirects(response, reverse('registration_success'))
        self.assertTrue(Student.objects.filter(student_id='TEST-001').exists())

        success_response = self.client.get(reverse('registration_success'))
        self.assertEqual(success_response.status_code, 200)
        self.assertContains(success_response, 'Student Registered Successfully!')


class StaffAuthenticationTests(TestCase):
    def test_login_page_and_successful_login_redirect(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'Staff Login')

        get_user_model().objects.create_user(
            username='staff',
            password='test-password',
            is_staff=True,
        )
        response = self.client.post(
            reverse('login'),
            {'username': 'staff', 'password': 'test-password'},
        )
        self.assertRedirects(response, reverse('staff_dashboard'))

    def test_invalid_login_displays_error_without_authenticating(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'unknown', 'password': 'incorrect'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password. Please try again.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_dashboard_and_student_management_require_staff(self):
        dashboard_url = reverse('staff_dashboard')
        protected_url = reverse('student_list')

        response = self.client.get(protected_url)
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={protected_url}',
        )

        student = Student.objects.create(
            student_id='TEST-STAFF-ONLY',
            first_name='Morgan',
            last_name='Record',
            gender='Male',
            date_of_birth='2001-01-01',
            contact_no='09123456780',
        )
        user = get_user_model().objects.create_user(
            username='regular',
            password='test-password',
        )
        self.client.force_login(user)
        protected_urls = (
            dashboard_url,
            protected_url,
            reverse('student_detail', args=[student.pk]),
            reverse('student_create'),
            reverse('student_update', args=[student.pk]),
            reverse('student_delete', args=[student.pk]),
        )
        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{reverse("login")}?next={url}',
                )

        user.is_staff = True
        user.save(update_fields=['is_staff'])
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome, regular!')
        self.assertContains(response, reverse('student_list'))

    def test_logout_requires_post_and_redirects_to_login(self):
        user = get_user_model().objects.create_user(
            username='staff',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

        protected_url = reverse('student_list')
        response = self.client.get(protected_url)
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={protected_url}',
        )
