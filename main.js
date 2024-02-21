const dotenv = require('dotenv');
dotenv.config();

const sdk = require('api')('@yelp-developers/v1.0#8e0h2zlqcimwm0');

// API documentation: https://docs.developer.yelp.com/reference/v3_business_search
// supported configs: https://blog.yelp.com/businesses/yelp_category_list/

sdk.auth(process.env.YELP_API_KEY);
sdk.v3_business_search({
  location: '94704',
  term: 'food',
  categories: 'bagels',
  sort_by: 'best_match',
  limit: '5'
})
  .then(({ data }) => console.log(data))
  .catch(err => console.error(err));