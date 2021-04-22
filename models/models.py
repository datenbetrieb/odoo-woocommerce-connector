# -*- coding: utf-8 -*-
from woocommerce import API

from odoo import models, fields, api, _
import requests
from requests.auth import HTTPBasicAuth
import time
import datetime
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class woocommerce_connector(models.Model):
    _name = 'woocommerce.configuration'
    _description = 'woocommerce.configuration'


    con_name = fields.Char(string='Connection Name')
    con_url = fields.Char(string='URL')
    con_endpoint = fields.Char(string='API Endpoint')
    consumer_key = fields.Char(string='Key')
    consumer_secret = fields.Char(string='Secret Key')
    user_id = fields.Integer(string='User ID')
    user_name = fields.Char(string='User Name')
    key_id = fields.Integer(string='WC Key ID')
    key_permissions = fields.Char(string='Permissions')
    last_synced = fields.Datetime(string='Last Synced')
    con_seq = fields.Char(string='Connection ID', required=True, copy=False, readonly=True,
                                                index=True, default=lambda self: _('New'))



    @api.model
    def create(self, vals):
        if vals.get('con_seq', _('New')) == _('New'):
            vals['con_seq'] = self.env['ir.sequence'].next_by_code('woocommerce.configuration.sequence') or _('New')
        result = super(woocommerce_connector, self).create(vals)
        return result

    @api.model
    def sync_woocommerce(self, vals):
        config_data = self.env['woocommerce.configuration'].search([])

        wcapi = API(
            url = config_data['con_url'],
            consumer_key = config_data['consumer_key'],
            consumer_secret = config_data['consumer_secret'],
            version = "wc/v3"
        )

        existing_products = self.env['woocommerce.products'].search([])
        ids_arr = []
        for obj in existing_products:
            ids_arr.append(str(obj['product_id']))
        ids = None
        if len(ids_arr) == 0:
            ids = None
        else:
            ids = ','.join(ids_arr)

        # excludes are highly likely busting the size limit of GET on large datasets
        #response = wcapi.get("products", params={"exclude": ids})
        response = wcapi.get("products")
        _logger.info('products ignore %s', ids)
        _logger.info('product status code %s', response.status_code)
        if not response.status_code == 200:
            msg = _('Failure %s with REST-Api on %s, check woocommerce-sync-settings and server-logs.') % (response.text[0:30], config_data['con_url'])
            raise UserError(msg)

        jsonObject = response.json()
 
        for data in jsonObject:
            vals= {
                'product_id': data['id'], 
                'name': data['name'], 
                'slug': data['slug'], 
                'permalink': data['permalink'], 
                'date_created': data['date_created'], 
                'date_created_gmt': data['date_created_gmt'], 
                'date_modified': data['date_modified'], 
                'date_modified_gmt': data['date_modified_gmt'], 
                'type': data['type'], 
                'status': data['status'], 
                'featured': data['featured'], 
                'catalog_visibility': data['catalog_visibility'], 
                'description': data['description'], 
                'short_description': data['short_description'], 
                'sku': data['sku'], 
                'price': data['price'], 
                'regular_price': data['regular_price'], 
                'sale_price': data['sale_price'], 
                'date_on_sale_from': data['date_on_sale_from'], 
                'date_on_sale_from_gmt': data['date_on_sale_from_gmt'], 
                'date_on_sale_to' : data['date_on_sale_to'],
                'price_html' : data['price_html'],
                'on_sale' : data['on_sale'],
                'purchasable' : data['purchasable'],
                'total_sales' : data['total_sales'],
                'virtual' : data['virtual'],
                'downloadable' : data['downloadable'],
                'downloads' : data['downloads'],
                'download_limit' : data['download_limit'],
                'download_expiry' : data['download_expiry'],
                'external_url' : data['external_url'],
                'button_text' : data['button_text'],
                'tax_status' : data['tax_status'],
                'tax_class' : data['tax_class'],
                'manage_stock' : data['manage_stock'],
                'stock_quantity' : data['stock_quantity'],
                'stock_status' : data['stock_status'],
                'backorders' : data['backorders'],
                'backorders_allowed' : data['backorders_allowed'],
                'backordered' : data['backordered'],
                'sold_individually' : data['sold_individually'],
                'weight' : data['weight'],
                'shipping_required' : data['shipping_required'],
                'shipping_taxable' : data['shipping_taxable'],
                'shipping_class' : data['shipping_class'],
                'shipping_class_id' : data['shipping_class_id'],
                'reviews_allowed' : data['reviews_allowed'],
                'average_rating' : data['average_rating'],
                'rating_count' : data['rating_count'],
                'parent_id' : data['parent_id'],
                'purchase_note' : data['purchase_note'],
                }
            model_products = self.env['woocommerce.products']
            model_products.create(vals)

            vals= {
                    'name': data['name'],                  
                    'list_price':  data['price'],  
                    'active': 'true',
                    'type': "product",
                    'categ_id': 2,
                    'default_code': data['id'], # this is the unique ID of a product of woocommerce - put it in internal reference field 'default_code'
                }
            _logger.info('creating product %s', data['name'])
            product_template = self.env['product.template']
            product_template.create(vals)
            self.env.cr.commit()

        existing_customers = self.env['woocommerce.customers'].search([])
        ids_arr = []
        for obj in existing_customers:
            ids_arr.append(obj['email'])
        ids = None
        if len(ids_arr) == 0:
            ids = None
        else:
            ids = ','.join(ids_arr)

        response = wcapi.get("customers", params={"exclude": ids, "role": "all"})
        _logger.info('customers ignore %s', ids)
        _logger.info('customer status code %s', response.status_code)
        if not response.status_code == 200:
            msg = _('Failure %s with REST-Api on %s, check woocommerce-sync-settings and server-logs.') % (response.text[0:100], config_data['con_url'])
            raise UserError(msg)

        jsonObject = response.json()
 
        for data in jsonObject:

            vals= {
                'customer_id': data['id'], 
                'date_created': data['date_created'], 
                'date_created_gmt': data['date_created_gmt'], 
                'date_modified': data['date_modified'], 
                'date_modified_gmt': data['date_modified_gmt'], 
                'email': data['billing']['email'],
                'first_name': data['first_name'], 
                'last_name': data['last_name'], 
                'role': data['role'], 
                'username': data['username'],
                'phone': data['billing']['phone'],
                'country': data['billing']['country'],
                'city':  data['billing']['city'],
                'street': data['billing']['address_1'],
                'street2': data['billing']['address_2'],  
                'zip': data['billing']['postcode'],
                }
            model_customers = self.env['woocommerce.customers']
            model_customers.create(vals)

            vals= {
                    'active': 'true',
                    'company_type': "person",
                    'category_id': [[6, 'false', []]],
                    'city':  data['billing']['city'],  
                    # 'country_id': data['billing']['country'],
                    'email': data['billing']['email'],
                    'mobile': data['billing']['phone'],
                    'name': data['first_name'] + " " + data['last_name'],                  
                    'phone': data['billing']['phone'], 
                    'ref': data['id'], # this is the unique ID of a customer of woocommerce
                    'street': data['billing']['address_1'],
                    'street2': data['billing']['address_2'],
                    'type': "delivery",
                    'zip': data['billing']['postcode'],
                    'customer_rank': 1,
                    'property_payment_term_id': 1,
                    # 'vat': "yeh sweden ki NIC hoga",
                }

            partner = self.env['res.partner'].search([('email','=', data['billing']['email'])])

            _logger.info('creating customer %s', vals['name'])
            res_partner = self.env['res.partner']
            res_partner.create(vals)
            self.env.cr.commit()

        existing_orders = self.env['woocommerce.orders'].search([])
        ids_arr = []
        for obj in existing_orders:
            ids_arr.append(str(obj['order_id']))
        ids = None
        if len(ids_arr) == 0:
            ids = None
        else:
            ids = ','.join(ids_arr)
 
        response = wcapi.get("orders", params={"exclude": ids})
        _logger.info('orders ignore %s', ids)
        _logger.info('orders status code %s', response.status_code)
        if not response.status_code == 200:
            msg = _('Failure with REST-API orders on %s, check woocommerce-sync-settings and server-logs. %s') % (config_data['con_url'], response.text[0:100])
            raise UserError(msg)

        jsonObject = response.json()
       
        for data in jsonObject:

            _logger.info("customer_id: %s, order id: %s", data['customer_id'], data['id'])

            vals= {
                'order_id': data['id'] , 
                'parent_id': data['parent_id'], 
                'number': data['number'], 
                'order_key': data['order_key'], 
                'created_via': data['created_via'], 
                'version': data['version'], 
                'status': data['status'], 
                'currency': data['currency'], 
                'date_created': data['date_created'], 
                'date_created_gmt': data['date_created_gmt'], 
                'date_modified': data['date_modified'], 
                'date_modified_gmt': data['date_modified_gmt'], 
                'discount_total': data['discount_total'], 
                'discount_tax': data['discount_tax'], 
                'shipping_total': data['shipping_total'], 
                'shipping_tax': data['shipping_tax'], 
                'cart_tax': data['cart_tax'], 
                'total': data['total'], 
                'total_tax': data['total_tax'], 
                'prices_include_tax': data['prices_include_tax'], 
                'customer_id': data['customer_id'], 
                'customer_ip_address': data['customer_ip_address'], 
                'customer_user_agent': data['customer_user_agent'], 
                'customer_note': data['customer_note'], 
                'payment_method' : data['payment_method'],
                'payment_method_title' : data['payment_method_title'],
                'transaction_id' : data['transaction_id'],
                'date_paid' : data['date_paid'],
                'date_paid_gmt' : data['date_paid_gmt'],
                'date_completed' : data['date_completed'],
                'date_completed_gmt' : data['date_completed_gmt'],
                'cart_hash' : data['cart_hash'],
                }
            model_orders = self.env['woocommerce.orders']
            model_orders.create(vals)

            _logger.info("customer_id: %s", data['customer_id'])
            _logger.info("data_created: %s", data['date_created'].replace("T",""))

            # @todo: be aware of problems with non unique mail-adresses
            partner = self.env['res.partner'].search([('email','=', data['billing']['email'])], limit=1)
            _logger.info(partner.id)
            #partner = self.env['res.partner'].search([('ref','=', data['customer_id'])])
            vals= {
                # 'note': data['id'], # this is the unique ID of a order of woocommerce
                'date_order': data['date_created'].replace("T", " "), 
                'partner_id': partner.id, 
                'warehouse_id': 1,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
                }

            _logger.info("creating order %s from customer %s", data['id'], data['billing']['email'])
            _logger.info("vals %s", vals)
            sale_order = self.env['sale.order']
            values = sale_order.create(vals)
            sale_order_id = values.id

            for lines in data['line_items']:
                product = self.env['product.product'].search([('barcode', '=', lines['product_id'])])
                order_line = {
                        'order_id': sale_order_id,
                        'product_id': product.id,
                        'price_unit': lines['price'],
                        'product_uom_qty': lines['quantity'],
                        'name': '@fixme',
                    }
                sale_order_line = self.env['sale.order.line']
                #new_line = sale_order_line.create(order_line)
                
        config_data.last_synced = datetime.datetime.now()

